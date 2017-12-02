from threading import Thread
import time
from user_agent import generate_user_agent
import requests
import subprocess


class BaseSourceWorker(Thread):
    def __init__(self, parent=None, id=0, stop_event=None):
        super().__init__()
        if parent:
            self.id  = id
            self.in_q = parent.source_q
            self.out_q = parent.parse_q
            self.parent = parent
            self.stop_event = stop_event
        self.mean = 0
        self.total_time = 0
        self.visited = 0

    def __call__(self, **kwargs):
        return self.__class__(**kwargs, **self.inits)

    def run(self):
        print('started')
        while not self.stop_event.wait(0):
            start = time.time()
            source = self.retrieve(self.in_q.get())
            if source:
                self.out_q.put(source)
            self.visited += 1
            self.total_time += time.time() - start
            self.mean = self.total_time / self.visited
            self.in_q.task_done()
        print('Done')

    def retrieve(self):
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
        self.user_agent = self.parent.model.user_agent

        self.connection_errors = []

    def retrieve(self, source):
        headers = {'User-Agent': generate_user_agent()
                    if not self.user_agent else self.user_agent}

        try:
            func = getattr(self.session, source.method)
            page = func(source.url, data=source.data,
                        params=source.params,
                        headers={**headers, # noqa
                                    **source.headers})
            # print(id(self), '{}'.format(source.url), page, source.method, source.data)

            if page and source.parse:
                source.data = page.text
                return source
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

#TODO fix the FileWorker class to the new spec.
class FileWorker(Thread):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.in_q = in_q
        self.out_q = out_q

    def retrieve(self, source):
        with open(template.url) as fle:
            lines = fle.readlines()
        return lines


class ProgramSource(BaseSourceWorker):
    def __init__(self, function='', *args, **kwargs):
        print(kwargs)
        super().__init__(*args, **kwargs)
        self.function = function
        self.inits = {'function': function}

    def retrieve(self, source):
        result = subprocess.run(self.function + source.url, shell=True,
                                stdout=subprocess.PIPE)
        source.data = result.stdout.decode('utf-8')
        return source
