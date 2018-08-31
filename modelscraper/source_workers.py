from threading import Thread
import time
import subprocess
import importlib
import logging
import traceback
import sys

import requests
from user_agent import generate_user_agent


def _read_zip_file(zipfile):
    content = ''
    with ZipFile(BytesIO(zipfile)) as myzip:
        for file_ in myzip.namelist():
            with myzip.open(file_) as fle:
                content += fle.read().decode('utf8')
    return content


class BaseSourceWorker(Thread):
    def __init__(
            self, parent, id=None, in_q=None, out_q=None,
            to_parse=None, semaphore=None):
        super().__init__()
        self.parent = parent
        self.id = id
        self.in_q = in_q
        self.out_q = out_q
        self.to_parse = to_parse
        self.mean =0
        self.total_time = 0
        self.visited = 0
        self.retrieving = False
        self.semaphore = semaphore

    def run(self):
        print('started source worker', self)
        while True:
            start = time.time()
            item = self.in_q.get()
            if item is None:
                break
            url, attrs = item
            with self.semaphore:
                self.retrieving = True
                data, increment = self.retrieve(url)
            self._recalculate_mean(start)

            if data:
                if self.parent.compression == 'zip':
                    data = self._read_zip_file(source.data)
                self.out_q.put((url, attrs, data))

            self.in_q.task_done()
            self.retrieving = False

    def retrieve(self):
        raise NotImplementedError

    def _recalculate_mean(self, start):
        self.visited += 1
        self.total_time += time.time() - start
        return self.total_time / self.visited


class WebSourceWorker(BaseSourceWorker):
    '''
    This class is used as a downloader for pages.
    It will place all items in its queue into the out_q specified.
    For use without parent Thread supply keyword arguments: name, domain, in_q,
    '''
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.retries = parent.retries
        self.session = parent.session
        self.time_out = parent.time_out
        self.user_agent = parent.user_agent

    def extract_json(self, response):
        data = response.json()
        for key in self.json_key:
            data = data.get(key, {})
            if not data:
                logging.warning('JSON key {} failed'.format(key))
        return data, 1

    def retrieve(self, url):
        headers = {'User-Agent': generate_user_agent()
                   if not self.user_agent else self.user_agent,
                   **self.parent.kws.pop('headers', {})}
        try:
            time.sleep(self.time_out)
            func = getattr(self.session, self.parent.func)
            response = func(url, headers=headers, **self.parent.kws) # noqa

            if response:
                if self.json_key:
                    data = self.extract_json(response)
                else:
                    data = page.text
                return data, 1
            else:
                return False, -1

        # Retry later with a timeout,
        except requests.Timeout:
            self.in_q.put(url)
            return False, 0

        # Retry later with connection error.
        except requests.ConnectionError:
            self.in_q.put(url)
            time.sleep(self.time_out)
            return False, 0

        except Exception as E:
            print(self.__class__.__name__, id(self), E)
            print(traceback.print_tb(sys.exc_info()[-1]))
            return False, -1


class FileSourceWorker(BaseSourceWorker):
    def retrieve(self, url):
        try:
            with open(url) as fle:
                return fle.read(), 1
        except FileNotFoundError:
            print('file not found', url)
            return False, -1


class ProgramSourceWorker(BaseSourceWorker):
    def retrieve(self, url):
        function = self.parent.func.format(url)
        result = subprocess.run(function, shell=True,
                                stdout=subprocess.PIPE)
        try:
            stdout = result.stdout
            return stdout.decode('utf-8'), 1
        except Exception as E:
            logging.log(logging.WARNING, 'Could not decode the result from ' +
                        function + ':\n ' + stdout)
            return False, -1

class ModuleSourceWorker(BaseSourceWorker):

    """Generates data by calling another modules function."""

    def __init__(self, module=None, conversion=None, *args, **kwargs):
        """@todo: to be defined1.

        :module_name: @todo

        """
        super().__init__(*args, **kwargs)

        self.module = module
        self.conversion = conversion
        self.inits = {'module': self.module,
                      'conversion': conversion}

    def retrieve(self, url):
        """Returns the data gotten by the source

        :source: @todo
        :returns: @todo

        """
        for name in self.parent.func.split('.'):
            function = getattr(self.module, name)
        try:
            data = function(url, **self.parent.kws)
            if self.conversion:
                data = self.conversion(data)
            return data, 1
        except Exception as E:
            logging.warning(' : '.join([str(E), url, str(self.parent.kws)]))
            return False, -1


class APISourceWorker(BaseSourceWorker):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.api_function = parent.api_function
        self.batch = parent.batch

    def retrieve_batch(self, urls):
        return self.api_function(urls[0] if type(urls) == list else urls)

    def run(self):
        print('started', self.__class__.__name__, id(self))
        while True:
            start = time.time()
            url = self.in_q.get()
            if url is None:
                break
            self.retrieving = True
            data = self.retrieve(url)
            # source = self.retrieve(self.in_q.get())
            if data:
                self.out_q.put(data)
            self.visited += 1
            self.total_time += time.time() - start
            self.mean = self.total_time / self.visited
            self.in_q.task_done()
            self.retrieving = False
