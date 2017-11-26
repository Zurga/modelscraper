from threading import Thread
import time
from user_agent import generate_user_agent
import requests
import subprocess


class BaseSourceWorker(Thread):
    def __init__(self, parent=None, id=0):
        super().__init__()
        if parent:
            self.id  = id
            self.in_q = parent.source_q
            self.out_q = parent.parse_q
            self.parent = parent

    def __call__(self, **kwargs):
        return self.__class__(**{**kwargs, **self.__dict__})

    def run(self):
        raise NotImplementedError


class WebSource(BaseSourceWorker):
    '''
    This class is used as a downloader for pages.
    It will place all items in its queue into the out_q specified.
    For use without parent Thread supply keyword arguments: name, domain, in_q,
    '''
    def __init__(self, time_out=0.3, retries=10, **kwargs):
        super().__init__(**kwargs)
        self.domain = self.parent.model.domain
        self.name = self.parent.name + 'WebSource ' + str(self.id)
        self.retries = retries
        self.session = self.parent.model.session
        self.time_out = time_out
        self.times = []
        self.to_parse = self.parent.to_parse
        self.mean = 0
        self.total_time = 0
        self.visited = 0
        self.user_agent = self.parent.user_agent

        self.connection_errors = []

    def run(self):
        while True:
            source = self.in_q.get()

            if source is None:
                self.in_q.task_done()
                print('stopped get')
                break

            headers = {'User-Agent': generate_user_agent()
                       if not self.user_agent else self.user_agent}

            try:
                func = getattr(self.session, source.method)
                page = func(source.url, data=source.data,
                            params=source.params,
                            headers={**headers, # noqa
                                     **source.headers})
                self.visited += 1
                self.total_time += page.elapsed.total_seconds()
                self.mean = self.total_time / self.visited
                # print(id(self), '{}'.format(source.url), page, source.method, source.data)

                if page and source.parse:
                    source.data = page.text
                    self.out_q.put(source)
                else:
                    print(source.url)
                    print(page)
                    print('No parsing required')

                time.sleep(self.time_out)
            # Retry later with a timeout,
            except requests.Timeout:
                print('timeout')
                self.in_q.put(source)

            # Retry later with connection error.
            except requests.ConnectionError:
                print('connection error')
                self.in_q.put(source)

                time.sleep(self.time_out)

            except Exception as E:
                print(E)
                self.to_parse -= 1
            self.in_q.task_done()


#TODO fix the FileWorker class to the new spec.
class FileWorker(Thread):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.in_q = in_q
        self.out_q = out_q

    def run(self):
        while True:
            getter = self.in_q.get()
            if template is None:
                print('stopping')
                break
            with open(template.url) as fle:
                lines = fle.readlines()
                self.out_q.put((self.parser.parse(lines), db, col))


class ProgramSource(BaseSourceWorker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mean = 0
        self.total_time = 0
        self.visited = 0

    def run(self):
        while True:
            source = self.in_q.get()

            if source is None:
                self.in_q.task_done()
                print('stopped', self.__name__)
                break

            result = subprocess.run(source.url, shell=True,
                                    stdout=subprocess.PIPE)
            source.data = result.stdout.decode('utf-8')
            print(source.data)
            self.out_q.put(source)
