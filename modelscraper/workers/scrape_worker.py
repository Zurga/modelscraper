import gzip
import os
import time
from collections import defaultdict
from multiprocessing import Process
from queue import Queue, Empty
from sys import stdout
from zipfile import ZipFile
from threading import Lock
import logging
import traceback
import sys

from pybloom_live import ScalableBloomFilter
from diskcache import Deque

from ..components import Attr


class ScrapeWorker(Process):
    def __init__(self, model):
        super().__init__()

        self.source_q = Queue()
        self.parse_q = Queue()
        self.seen = ScalableBloomFilter()
        self.forwarded = ScalableBloomFilter()
        self.new_sources = []
        self.workers = []
        self.to_forward = Deque()
        self.parser = None
        self.dbs = dict()
        self.schedule = model.schedule
        self.model = model
        self.total_time = 0
        self.lock = Lock()

        # Start all the threads necessary for storing the data
        for thread in model.db_threads:
            print(thread)
            thread.start()

    def run(self):
        # create the threads needed to scrape
        i = 0
        while i < len(self.model.phases):
            phase = self.model.phases[i]
            self.phase = i
            # Check if the phase has a parser, if not, reuse the one from the
            # last phase.
            self.to_parse = 0
            self.parsed = 0

            if phase.active:
                self.spawn_workforce(phase)

                if not phase.sources:
                    phase.sources = (source for source in self.to_forward)

                self.to_forward = Deque()
                self.feed_sources(phase, amount=phase.n_workers + 1)

                source = self.consume_source()
                while source and self.to_parse != self.parsed:
                    self.feed_sources(phase, int(phase.n_workers / 2) + 2)

                    start = time.time()
                    # TODO add custom template if a source has a template
                    for template in phase.templates:
                        template.parse(source)
                        template.to_store()

                    self.total_time += time.time() - start
                    self.parsed += 1

                    for source in self._gen_sources(self.model.new_sources):
                        self._add_source(source)

                    self.model.new_sources = []

                    self.show_progress()
                    source = self.consume_source()

            if not phase.repeat:
                i += 1
        self._kill_workers()
        for db in self.model.dbs.values():
            db.store_q.put(None)
        for db in self.model.dbs.values():
            db.store_q.join()
        print('Waiting for the database')
        print('Scraper fully stopped')

    def feed_sources(self, phase, amount=1):
        if phase.sources:
            if type(phase.sources) == tuple or type(phase.sources) == list:
                for source in phase.sources:
                    self.source_q.put(source)
                    self.to_parse += 1
                phase.sources = False
            else:
                added = 0
                for _ in range(amount):
                    try:
                        self.source_q.put(phase.sources.send(None))
                        added += 1
                    except StopIteration:
                        continue
                self.to_parse += added

    def consume_source(self):
        """
        Blocking function which will poll the parse queue for a source with a
        timeout of 10 seconds.
        """
        while True:
            try:
                source = self.parse_q.get(timeout=10)
                self.seen.add(source.url)

                if source.compression == 'zip':
                    source.data = self._read_zip_file(source.data)
                return source
            except Empty:
                # Break out of the while loop if there are no sources to
                # parse and the workers are not busy retrieving a source.
                if self.source_q.empty() and all(worker.retrieving == False
                                                for worker in self.workers):
                    print('No more sources to parse at this point')
                    return False
                else:
                    print('Waiting for sources to parse')

    def _kill_workers(self):
        logging.log(logging.DEBUG, "Killing workers")
        if self.workers:
            for worker in self.workers:
                self.source_q.put(None)
            for worker in self.workers:
                worker.join()
        logging.log(logging.DEBUG, "Workers killed")

    def spawn_workforce(self, phase):
        # Kill existing workers if there are any
        self._kill_workers()

        if phase.n_workers:
            n_workers = phase.n_workers
        else:
            n_workers = self.model.num_getters

        self.workers = [phase.source_worker(in_q=self.source_q,
                                            out_q=self.parse_q,
                                            lock=self.lock,
                                            to_parse=self.to_parse,
                                            id=i)
                        for i in range(n_workers)]
        for worker in self.workers:
            worker.start()

    def get_scraped_urls(self, phase):
        for template in phase.templates:
            if template.name in self.dbs:
                for objct in self.dbs[template.name].read(template):
                    if objct:
                        yield objct.attrs['url'].value

    def _gen_sources(self, source_list):
        for objct, attr, values in source_list:
            for value in values:
                # for now only "or" is supported.
                if attr.source_condition and not \
                        self._evaluate_condition(objct, attr):
                        continue

                attrs = []

                if attr.source.copy_attrs:
                    attrs_to_copy = attr.source.copy_attrs
                    assert all(attr in objct for attr in attrs_to_copy)
                    if type(attrs_to_copy) == dict:
                        # We store the copied attributes under different names.
                        for key, value in attrs_to_copy.items():
                            attrs.append(Attr(name=value, value=objct[key]))
                    else:
                        for key in attrs_to_copy:
                            attrs.append(Attr(name=key, value=objct[key]))
                if attr.source.parent:
                    _parent = Attr(name='_parent', value=(objct['url'],))
                    attrs.append(_parent)

                yield attr.source(url=value, attrs=attrs)

    def _add_source(self, source):
        if source.url and (source.url not in self.seen or source.duplicate) \
                and source.url not in self.forwarded:
            if source.active:
                self.to_parse += 1
                self.source_q.put(source)
                self.seen.add(source.url)
            else:
                self.to_forward.append(source)
                self.forwarded.add(source.url)

    def value_is_new(self, objct, uri, name):
        db_objct = self.db.read(uri, objct)
        if db_objct and db_objct.attrs.get(name):
            if db_objct.attrs[name].value != objct.attrs[name].value:
                return True
            return False

    def _evaluate_condition(self, objct, attr, **kwargs):
        expression = ''

        for operator, attrs in attr.source_condition.items():
            expression += (' '+operator+' ').join(
                [str(value) + c for name, c in attrs.items()
                    for value in objct[name]])
        if expression:
            return eval(expression, {}, {})
        else:
            return False

    def show_progress(self):
        os.system('clear')
        info = '''
        Domain              {}
        Phase               {}
        Sources to get:     {}
        Sources to parse:   {}
        Sources parsed:     {} {}%
        Average get time:   {}s
        Average parse time: {}s
        '''
        get_average = sum(w.mean for w in self.workers) / len(self.workers)
        print(info.format(self.name,
                          self.phase,
                          self.source_q.qsize(),
                          self.to_parse,
                          self.parsed, (self.parsed / self.to_parse) * 100,
                          round(get_average, 3),
                          round(self.total_time / self.parsed, 3)
                          ))

    def _read_zip_file(self, zipfile):
        content = ''
        with ZipFile(BytesIO(zipfile)) as myzip:
            for file_ in myzip.namelist():
                with myzip.open(file_) as fle:
                    content += fle.read().decode('utf8')
        return content

    def _read_gzip_file(self, gzfile):
        with gzip.open(BytesIO(gzfile)) as fle:
            return fle.read()


class DummyScrapeWorker(ScrapeWorker):
    def __init__(self, model):
        # Unset all the phase settings
        for phase in model.phases:
            phase.n_workers = 1
        super().__init__(model)
        self.to_forward = []
        self.to_parse = 0
        self.parsed = 0

    def run(self):
        for phase in self.model.phases:
            self.spawn_workforce(phase)

            if not phase.sources:
                phase.sources = self.to_forward[:1]

            self.to_forward = []
            self.feed_sources(phase)
            print(self.to_parse, 'sources in queue')
            source = self.consume_source()
            print(source.url)
            for template in phase.templates:
                try:
                    template.parse(source)
                    print(template.name)
                    for obj in template.objects:
                        for name, value in obj.items():
                            print('\t', name, ':', value)
                except Exception as E:
                    print(E, template)
                    print(traceback.print_tb(sys.exc_info()[-1]))

            print('generated', len(self.model.new_sources), 'new sources')
            for source in self._gen_sources(self.model.new_sources[:]):
                if source.active == False:
                    self._add_source(source)
            print('forwarded', len(self.to_forward))

            self.model.new_sources = []
