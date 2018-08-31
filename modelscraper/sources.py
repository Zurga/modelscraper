import attr
from attr import Factory
import importlib
import logging
import subprocess
import time
from queue import Queue, Empty
from threading import Thread, BoundedSemaphore

from user_agent import generate_user_agent
import requests
from pybloom_live import ScalableBloomFilter

from .source_workers import WebSourceWorker, FileSourceWorker, \
    ProgramSourceWorker, ModuleSourceWorker, APISourceWorker


@attr.s(hash='in_q')
class Source(object):
    name = attr.ib('')
    compression = attr.ib('')
    duplicate = attr.ib(False)
    func = attr.ib('get')
    kws = attr.ib(Factory(dict))
    n_workers = attr.ib(default=1)
    in_q = attr.ib(Factory(Queue))
    out_q = attr.ib(Factory(Queue))
    url_template = attr.ib('{}')
    urls = attr.ib(Factory(list))
    seen = attr.ib(Factory(ScalableBloomFilter))
    to_parse = attr.ib(0)
    lock = attr.ib(None)
    _semaphore = attr.ib(None)
    attrs = attr.ib(Factory(list))

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
                               to_parse=self.to_parse)
            for _ in range(self.n_workers)]

        for worker in self.workers:
            worker.start()

    def __attrs_post_init__(self):
        self.url_amount = int((self.n_workers / 2) + 2)
        if not self.urls:
            self.received = False
        else:
            self.received = True

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

    def __iter__(self):
        assert self.workers, "No workers have been started, call 'initialize_workers'"
        self.consume()
        try:
            url, attrs, data = self.out_q.get(timeout=1)
            print('__iter__', url)
            self.out_q.task_done()
            yield url, attrs, data
        except Empty:
            print(self.name, 'is empty')
            if self.received and not all(w.retrieving for w in self.workers):
                print('stopping source', self.name)
                yield None

    def consume(self):
        if self.urls:
            if type(self.urls) is list:
                for _ in range(self.url_amount):
                    try:
                        url = self.urls.pop()
                    except IndexError:
                        self.urls = False
            else:
                for _ in range(self.url_amount):
                    try:
                        url = next(self.urls)
                    except StopIteration:
                        self.urls = False

            if self.attrs and type(self.attrs) is list:
                attrs = self.attrs.pop()
            else:
                attrs = {}

            url = self.url_template.format(url)
            self.in_q.put((url, attrs))
            self.seen.add(url)

    def add_source(self, url, attrs):
        self.received = True
        url = self.url_template.format(url)
        if url not in self.seen or self.repeat:
            print('adding', url)
            self.in_q.put((url, attrs))
            self.seen.add(url)
            print(self.in_q.qsize())

@attr.s
class WebSource(Source):
    source_worker = WebSourceWorker
    retries = attr.ib(10)
    session = attr.ib(requests.Session())
    domain = attr.ib('')
    user_agent = attr.ib('')
    cookies = attr.ib(Factory(dict))
    time_out = attr.ib(1)
    json_key = attr.ib('')

    def __attrs_post_init__(self):
        if self.cookies:
            requests.utils.add_dict_to_cookiejar(self.session.cookies,
                                                 self.cookies)

class FileSource(Source):
    source_worker = FileSourceWorker

class ProgramSource(Source):
    source_worker = ProgramSourceWorker

class ModuleSource(Source):
    source_worker = ModuleSourceWorker

class APISource(Source):
    source_worker = APISourceWorker
