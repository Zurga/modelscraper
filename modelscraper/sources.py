from multiprocessing import JoinableQueue
from queue import Empty
from threading import BoundedSemaphore
import logging
import types

import requests
from user_agent import generate_user_agent
from pybloom_live import ScalableBloomFilter

from .helpers import str_as_tuple
from .source_workers import WebSourceWorker, FileSourceWorker, \
    ProgramSourceWorker, ModuleSourceWorker, APISourceWorker


class Source(object):
    def __init__(self, name='', kws={}, attrs=[], url_template='{}',
                 urls=[], test_urls=[], n_workers=1, compression='',
                 kwargs_format={}, duplicate=False, repeat=False):
        self.attrs = attrs
        self.compression = compression
        self.duplicate = duplicate
        self.kwargs_format = kwargs_format
        self.kws = kws
        self.n_workers = n_workers
        self.name = name
        self.repeat = repeat
        self.url_template = url_template
        self.urls = urls

        self.in_q = JoinableQueue()
        self.out_q = JoinableQueue()
        self.kwargs = []
        self.seen = ScalableBloomFilter()
        self.test_urls = str_as_tuple(test_urls)
        self._semaphore = BoundedSemaphore(self.n_workers)
        self.url_amount = int((self.n_workers / 2) + 10)
        self.to_parse = 0
        if not self.urls:
            self.received = False
        else:
            self.received = True

    @property
    def semaphore(self):
        return self._semaphore

    @semaphore.setter
    def semaphore(self, semaphore):
        if semaphore._value == self.n_workers:
            self._semaphore = semaphore
        else:
            self._semaphore = BoundedSemaphore(self.n_workers)
        self.initialize_workers()

    def initialize_workers(self):
        self.workers = [
            self.source_worker(parent=self, id=1, in_q=self.in_q,
                               out_q=self.out_q, semaphore=self._semaphore,
                               )
            for _ in range(self.n_workers)]

        for worker in self.workers:
            worker.start()

    @classmethod
    def from_db(cls, template, url='url', query={}, **kwargs):
        db_type = template.db_type[0]

        # Check if the database has been instantiated by the Scrapeworker
        if isinstance(db_type, type):
            db_type = db_type()
        elif type(db_type) is str:
            db_type = getattr(databases, db_type)()
        for t in db_type.read(template=template, query=query):
            attr = t.attrs.get(url, [])
            if type(attr.value) is not list:
                values = [attr.value]
            else:
                values = attr.value
            for v in values:
                yield cls(url=v, **kwargs)

    def get_source(self):
        assert self.workers, "No workers have been started, call \
            'initialize_workers'"
        self.consume()

        try:
            url, attrs, data = self.out_q.get(timeout=1)
            self.out_q.task_done()
            self.to_parse -= 1
            return url, attrs, data
        except Empty:
            if self.received and not self.to_parse and not all(
                    w.retrieving for w in self.workers):
                print('stopping source', self.name)
                for worker in self.workers:
                    self.in_q.put(None)
                for worker in self.workers:
                    worker.join()
                return False
        return None

    def consume(self):
        for _ in range(self.url_amount):
            if self.urls:
                if type(self.urls) is list:
                    try:
                        url = self.urls.pop()
                    except IndexError:
                        self.urls = False
                        break
                elif isinstance(self.urls, types.GeneratorType):
                    try:
                        url = next(self.urls)
                    except StopIteration:
                        self.urls = False
                        break

                if self.attrs and type(self.attrs) is list:
                    attrs = self.attrs.pop()
                else:
                    attrs = {}
                kwargs = self.get_kwargs()

                url = self.url_template.format(url)
                self.in_q.put((url, attrs, kwargs))
                self.to_parse += 1
                self.seen.add(url)

    def add_source(self, url, attrs, objct={}):
        self.received = True
        url = self.url_template.format(url)
        if url not in self.seen or self.repeat:
            kwargs = self.get_kwargs(objct)
            self.in_q.put((url, attrs, kwargs))
            self.to_parse += 1
            self.seen.add(url)

    def get_kwargs(self, objct=None):
        kwargs = {}
        for key in self.kwargs:
            value = getattr(key, self)
            if value:
                if type(value) is list:
                    value = value.pop(0)
                elif type(value) is dict:
                    kwargs[key] = value
                    continue
                else:
                    try:
                        value = next(value)
                    except StopIteration:
                        continue

                if objct and key in self.kwargs_format:
                    value = value.format(**{k:objct[k] for k in
                                            self.kwargs_format[key]})
                kwargs[key] = value
        return kwargs

class WebSource(Source):
    kwargs = ('headers', 'data', 'form', 'params')
    source_worker = WebSourceWorker

    def __init__(self, cookies=None, data=[], domain='', form=[],
                 func='get', headers={}, json_key='', params=[],
                 retries=10, session=requests.Session(),
                 time_out=1, user_agent='', *args, **kwargs):
        print(args, kwargs)
        super().__init__(*args, **kwargs)
        self.cookies = cookies
        self.data = data
        self.domain = domain
        self.form = form
        self.func = func
        self.headers = headers
        self.json_key = json_key
        self.params = params
        self.retries = retries
        self.session = session
        self.time_out = time_out
        self.user_agent = user_agent

        if self.cookies:
            print('cookies', self.cookies)
            requests.utils.add_dict_to_cookiejar(self.session.cookies,
                                                 self.cookies)

    def get_kwargs(self, objct=None):
        if not self.user_agent:
            user_agent = generate_user_agent()
        else:
            user_agent = self.user_agent
        kwargs = {
            'headers': {
                'User-Agent': user_agent
            },
            **super().get_kwargs(objct)}
        return kwargs

    def add_source(self, url, attrs, objct):
        if self.domain in url:
            super().add_source(url, attrs, objct)

class FileSource(Source):
    source_worker = FileSourceWorker
    kwargs = ['buffering']
    func = open

class ProgramSource(Source):
    source_worker = ProgramSourceWorker

class ModuleSource(Source):
    source_worker = ModuleSourceWorker

class APISource(Source):
    source_worker = APISourceWorker
