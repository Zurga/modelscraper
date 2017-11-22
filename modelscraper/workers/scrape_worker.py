from collections import defaultdict
from multiprocessing import Process, JoinableQueue
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
import os
import time

from pybloom import ScalableBloomFilter, BloomFilter

from .. import databases


class ScrapeWorker(Process):
    def __init__(self, model):
        super(ScrapeWorker, self).__init__()

        self.source_q = Queue()
        self.parse_q = JoinableQueue()
        self.seen = ScalableBloomFilter()
        self.forwarded = ScalableBloomFilter()
        self.new_sources = []
        self.workers = []
        self.to_forward = []
        self.parser = None
        self.done_parsing = False
        self.no_more_sources = False
        self.dbs = dict()
        self.schedule = model.schedule
        self.model = model

        for attr in model.__dict__.keys():
            setattr(self, attr, getattr(model, attr))

        db_threads = defaultdict(list)

        for run in model.runs:
            for template in run.templates:
                if template.db_type:
                    db_threads[template.db_type].append(template)
                self.check_functions(template, run)

        for thread, templates in db_threads.items():
            queue = JoinableQueue()
            store_thread = databases._threads[thread](store_q=queue)

            for template in templates:
                self.dbs[template.name] = store_thread
            store_thread.start()

    def run(self):
        # create the threads needed to scrape
        i = 0
        while self.runs:
            # if self.is_scheduled():
            if i < len(self.runs):
                run = self.runs[i]
            else:
                break
            print('running run:', i, run.name)
            i += 1

            # Check if the run has a parser, if not, reuse the one from the
            # last run.
            self.to_parse = 0
            self.parsed = 0

            if run.active:
                self.spawn_workforce(run)
                self.add_sources(run)
                self.to_forward = []
                self.parse_sources()

            if run.repeat:
                self.runs.append(run)
                print('Repeating run:', run.name)
            # else:
            #time.sleep(self.get_sleep_time())
        print('Run:', i, 'stopped')

    def parse_sources(self):
        while True:
            if self.to_parse == self.parsed:
                break
            try:
                source = self.parse_q.get(timeout=10)
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
                self.seen.add(source.url)
                objects = self.parser.parse(source)
                self.parsed += 1

                for obj in objects:
                    if obj.db:
                        self.dbs[obj.name].store_q.put(obj)

                for new_source in self.new_sources:
                    self._gen_source(*new_source)

                self.new_sources = []
                self.show_progress()

        print('parser_joined')
        print('Unparsed ', self.source_q.qsize())

    def spawn_workforce(self, run):
        # check if run reuses the current source workforce
        if run.parser:
            self.parser = run.parser(parent=self, templates=run.templates)
        elif not self.parser and not run.parser:
            raise Exception('No parser was specified')
        else:
            parse_class = self.parser.__class__
            self.parser = parse_class(parent=self, templates=run.templates)

        if run.n_workers:
            n_workers = run.n_workers
        else:
            n_workers = self.model.num_getters

        if not self.workers:
            for i in range(n_workers):
                worker = run.source_worker(parent=self, id=i,
                                           out_q=self.parse_q,
                                           time_out=self.time_out)
                worker.start()
                self.workers.append(worker)

    def add_sources(self, run):
        urls_in_db = []
        if run.synchronize:
            urls_in_db = [url for url in self.get_scraped_urls(run)]

        for source in self.to_forward:
            if source.url not in urls_in_db:
                self.source_q.put(source)
                self.to_parse += 1

        for source in run.sources:
            if source.from_db:
                sources = self.dbs[source.from_db].read(source.from_db)
            if source.active:
                self.source_q.put(source)
                self.to_parse += 1

    def get_scraped_urls(self, run):
        for template in run.templates:
            if template.name in self.dbs:
                for objct in self.dbs[template.name].read(template):
                    if objct:
                        yield objct['url'].value

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
        if attr.source_condition:
            for name, cond in attr.source_condition.items():
                values = objct.attrs[name].value
                # Wrap the value in a list without for example seperating the
                # characters.
                values = [values] if type(values) != list else values
                for val in values:
                    if val and not eval(str(val) + cond, {}, {}):
                        return False
        return True

    def reset_source_queue(self):
        while not self.source_q.empty():
            try:
                self.source_q.get(False)
            except Empty:
                continue
            self.source_q.task_done()

    def show_progress(self):
        os.system('clear')
        info = '''
        Domain              {}
        Sources to get:     {}
        Sources to parse:   {}
        Sources parsed:     {}
        Average get time:   {}s
        Average parse time: {}s
        '''
        get_average = sum(w.mean for w in self.workers) / len(self.workers)
        print(info.format(self.name,
                          self.source_q.qsize(),
                          self.to_parse,
                          self.parsed,
                          round(get_average, 3),
                          round(self.parser.total_time / self.parsed, 3)
                          ))

    def check_functions(self, template, run):
        error_string = "One of these functions: {} is not implemented in {}."
        not_implemented = []

        for attr in template.attrs.values():
            for func in attr.func:
                if not getattr(run.parser, func, False):
                    not_implemented.append(func)

        if not_implemented:
            raise Exception(error_string.format(str(not_implemented),
                                                run.parser.__class__.__name__))
