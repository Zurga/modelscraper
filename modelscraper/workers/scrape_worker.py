import gzip
import os
import time
from collections import defaultdict
from multiprocessing import Process
from queue import Queue, Empty
from sys import stdout
from threading import Event
from zipfile import ZipFile

from pybloom import ScalableBloomFilter


class ScrapeWorker(Process):
    def __init__(self, model):
        super(ScrapeWorker, self).__init__()

        self.source_q = Queue()
        self.parse_q = Queue()
        self.seen = ScalableBloomFilter()
        self.forwarded = ScalableBloomFilter()
        self.new_sources = []
        self.workers = []
        self.to_forward = []
        self.parser = None
        self.dbs = dict()
        self.schedule = model.schedule
        self.model = model
        self.source_kill = None
        self.dummy = model.dummy
        self.total_time = 0

        # Start all the threads necessary for storing the data and give each
        # template a reference to the thread it needs to store data in.
        for thread in set(model.dbs.values()):
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

                print(self.to_forward[:10])
                for source in self.to_forward:
                    self.source_q.put(source)
                    self.to_parse += 1

                self.to_forward = []
                self.parse_sources(phase)

            if not phase.repeat:
                i += 1
        for db in self.dbs.values():
            db.store_q.put(None)
        for db in self.dbs.values():
            db.store_q.join()
        print('Waiting for the database')
        print('Scraper fully stopped')

    def consume_sources(self, phase, amount=1):
        if phase.sources:
            if type(phase.sources) == tuple:
                for source in phase.sources:
                    self._add_source(source)
            else:
                for _ in range(amount):
                    self.source_q.put(phase.sources.send(None))
                    self.to_parse += 1

    def parse_sources(self, phase):
        self.consume_sources(phase, amount=phase.n_workers)
        while True:
            if self.to_parse == self.parsed:
                break
            try:
                source = self.parse_q.get(timeout=10)
                self.consume_sources(phase, int(phase.n_workers / 2) + 1)
            except Empty:
                if self.source_q.empty():
                    print('No more sources to parse at this point')
                    break
                # elif self.paused:
                #     time.sleep(self.get_sleep_time())
                else:
                    print('Waiting for sources to parse')
                    source = None

            if source is not None:
                start = time.time()
                self.seen.add(source.url)

                if source.compression == 'zip':
                    source.data = self._read_zip_file(source.data)
                # TODO add custom template if a source has a template

                for template in phase.templates:
                    i = 0
                    # Prepare the data based on multiple parsers
                    while i < len(template.parser) - 1:
                        parser = template.parser[i]
                        selector = template.selector[i]
                        source.data = parser.parse(source, template,
                                                   selector=selector,
                                                   gen_objects=False)
                        i += 1

                    parser = template.parser[i]
                    if template.selector:
                        selector = template.selector[i]
                    else:
                        selector = None
                    # Create the actual objects
                    objects = parser.parse(source, template=template,
                                                selector=selector)

                    template.objects = objects
                    if template.db:
                        self.model.dbs[id(template)].store_q.put(
                            template.to_store())
                self.parsed += 1

                for new_source in self.model.new_sources:
                    self._gen_source(*new_source)

                self.model.new_sources = []
                self.total_time += time.time() - start
                self.show_progress()

        print('Unparsed ', self.source_q.qsize())

    def spawn_workforce(self, phase):
        if phase.n_workers:
            n_workers = phase.n_workers
        else:
            n_workers = self.model.num_getters

        # Kill existing workers if there are any
        if self.workers:
            self.source_kill.set()

        # Create new Event to be able to kill the source workers
        self.source_kill = Event()
        self.workers = [phase.source_worker(parent=self, id=i,
                                       stop_event=self.source_kill)
                   for i in range(n_workers)]
        for worker in self.workers:
            worker.start()

    def add_sources(self, phase):
        #TODO check this!
        urls_in_db = []
        if phase.synchronize:
            urls_in_db = [url for url in self.get_scraped_urls(phase)]

    def get_scraped_urls(self, phase):
        for template in phase.templates:
            if template.name in self.dbs:
                for objct in self.dbs[template.name].read(template):
                    if objct:
                        yield objct.attrs['url'].value

    def _gen_source(self, objct, attr):
        for value in attr.value:
            # for now only "or" is supported.
            if not self._evaluate_condition(objct, attr):
                continue

            url = self._apply_src_template(attr.source, value)
            attrs = []

            if attr.source.copy_attrs:
                attrs_to_copy = attr.source.copy_attrs
                assert all(attr in objct.attrs for attr in attrs_to_copy)
                if type(attrs_to_copy) == dict:
                    # We store the copied attributes under different names.
                    for key, value in attrs_to_copy.items():
                        attrs.append(objct.attrs[key](name=value))
                else:
                    for key in attrs_to_copy:
                        attrs.append(objct.attrs[key]())
            if attr.source.parent:
                _parent = attr(name='_parent', value=(objct.url,))
                attrs.append(_parent)

            new_source = attr.source(url=url, attrs=attrs)

            if attr.attr_condition:
                if self.value_is_new(objct, value, attr.attr_condition):
                    self._add_source(new_source)
            else:
                self._add_source(new_source)

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

    def _apply_src_template(self, source, url):
        if source.src_template:
            # use formatting notation in the src_template
            return source.src_template.format(url)
        return url

    def _evaluate_condition(self, objct, attr, **kwargs):
        # TODO add "in", and other possibilities.
        expression = ''
        if attr.source_condition:
            for operator, attrs in attr.source_condition.items():
                expression += (' '+operator+' ').join(
                    [str(value) + c for name, c in attrs.items()
                     for value in objct.attrs[name].value])
            return eval(expression, {}, {})
        return True

    def reset_source_queue(self):
        while not self.source_q.empty():
            try:
                self.source_q.get(False)
            except Empty:
                continue
            self.source_q.task_done()

    def show_progress(self):
        if not self.dummy:
            os.system('clear')
        info = '''
        Domain              {}
        Phase               {}
        Sources to get:     {}
        Sources to parse:   {}
        Sources parsed:     {}
        Average get time:   {}s
        Average parse time: {}s
        '''
        get_average = sum(w.mean for w in self.workers) / len(self.workers)
        print(info.format(self.name,
                          self.phase,
                          self.source_q.qsize(),
                          self.to_parse,
                          self.parsed,
                          round(get_average, 3),
                          round(self.total_time / self.parsed, 3)
                          ))
        #stdout.flush()

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
