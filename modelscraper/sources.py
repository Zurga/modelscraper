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
        self.mean = 0
        self.total_time = 0
        self.visited = 0
        self.retrieving = False

    def __call__(self, **kwargs):
        return self.__class__(**kwargs, **self.inits)  # noqa

    def run(self):
        print('started', self.__class__.__name__, id(self))
        while True:
            start = time.time()
            source = self.in_q.get()
            if source is None:
                break
            self.retrieving = True
            source = self.retrieve(source)
            # source = self.retrieve(self.in_q.get())
            if source:
                self.out_q.put(source)
            self.visited += 1
            self.total_time += time.time() - start
            self.mean = self.total_time / self.visited
            self.in_q.task_done()
            self.retrieving = False
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
            time.sleep(self.time_out)
            func = getattr(self.session, source.method)
            page = func(source.url, data=source.data,
                        params=source.params,
                        headers={**headers, # noqa
                                    **source.headers})
        # Retry later with a timeout,
        except requests.Timeout:
            # print('timeout')
            self.in_q.put(source)

        # Retry later with connection error.
        except requests.ConnectionError:
            # print('connection error')
            self.in_q.put(source)

            time.sleep(self.time_out)

        except Exception as E:
            print(self.__class__.__name__, id(self), E)
            self.to_parse -= 1
        else:
            if page and source.parse:
                source.data = page.text
                return source
            else:
                self.to_parse -= 1


class FileSource(BaseSourceWorker):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def retrieve(self, source):
        with open(source.url) as fle:
            source.data = fle.read()
        return source


class ProgramSource(BaseSourceWorker):
    def __init__(self, function='', **kwargs):
        super().__init__(**kwargs)
        self.function = function
        self.inits = {'function': function}

    def retrieve(self, source):
        result = subprocess.run(self.function + source.url, shell=True,
                                stdout=subprocess.PIPE)
        source.data = result.stdout.decode('utf-8')
        return source


class APISource(BaseSourceWorker):
    def __init__(self, api_function=None, batch=1, **kwargs):
        super().__init__(**kwargs)
        self.api_function = api_function
        self.batch = batch

    def retrieve_batch(self, sources):
        return self.api_function(source[0] if type(sources) == list else source)

    def run(self):
        print('started', self.__class__.__name__, id(self))
        while True:
            start = time.time()
            source = self.in_q.get()
            if source is None:
                break
            self.retrieving = True
            source = self.retrieve(source)
            # source = self.retrieve(self.in_q.get())
            if source:
                self.out_q.put(source)
            self.visited += 1
            self.total_time += time.time() - start
            self.mean = self.total_time / self.visited
            self.in_q.task_done()
            self.retrieving = False
        print('Done')

