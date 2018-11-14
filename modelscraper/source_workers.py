from threading import Thread
import time
import subprocess
import logging
import traceback
import sys
import urllib
import json
from selenium.common.exceptions import JavascriptException

import requests
import dns.resolver

logger = logging.getLogger(__name__)

def _read_zip_file(zipfile):
    content = ''
    with ZipFile(BytesIO(zipfile)) as myzip:
        for file_ in myzip.namelist():
            with myzip.open(file_) as fle:
                content += fle.read().decode('utf8')
    return content


class BaseSourceWorker(Thread):
    def __init__(self, parent, id=None, in_q=None, out_q=None,
                 semaphore=None, lock=None):
        super().__init__()
        self.parent = parent
        self.id = id
        self.in_q = in_q
        self.lock = lock
        self.out_q = out_q
        self.mean = 0
        self.total_time = 0
        self.visited = 0
        self.retrieving = False
        self.semaphore = semaphore

    def run(self):
        while True:
            start = time.time()
            item = self.in_q.get()
            if item is None:
                break
            try:
                url, kwargs = item
            except:
                print(item, 'this went wrong')
            with self.semaphore:
                self.retrieving = True
                data = self.retrieve(url, kwargs)
            self._recalculate_mean(start)

            if data and self.parent.compression == 'zip':
                data = self._read_zip_file(source.data)
            self.out_q.put((url, data))

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
    The Worker class for the WebSource. Largely a wrapper around the requests
    module.
    '''
    def retrieve(self, url, kwargs):
        time.sleep(self.parent.time_out)
        try:
            response = self.parent.session.request(self.parent.func, url, **kwargs)
            if response:
                return response.text
            else:
                return False

        # Retry later with a timeout,
        except requests.Timeout:
            self.in_q.put((url, kwargs))
            with self.lock:
                self.parent.to_parse += 1
            return False

        # Retry later with connection error.
        except requests.ConnectionError:
            # Check if the host is online or the DNS can be reached
            try:
                print('checking if the domain is up')
                parsed = urllib.parse.urlparse(url)
                record = dns.resolver.query(parsed.netloc)
                self.in_q.put((url, kwargs))
                with self.lock:
                    self.parent.to_parse += 1
                time.sleep(self.parent.time_out)
                return False
            except dns.resolver.Timeout:
                return False

        except Exception as E:
            print(self.__class__.__name__, id(self), E)
            print(traceback.print_tb(sys.exc_info()[-1]))
            return False


class BrowserSourceWorker(WebSourceWorker):
    '''Source worker for the BrowserSource. By setting the script parameter in the
    BrowserSource instance, the result of the script will be appended to the HTML
    as JSON with the root tag: "<script id='result'></script>"
    '''
    def retrieve(self, url, kwargs):
        response_text = super().retrieve(url, kwargs)
        if self.parent.script:
            if response_text:
                try:
                    script_result = self.parent.session.execute_script(
                        self.parent.script)
                    try:
                        script_result = json.dumps(script_result)
                    except Exception as E:
                        print(str(E))
                    if self.parent.script_only:
                        return script_result
                    else:
                        return response_text + \
                            '<script id="result">{}<script>'.format(script_result)


                except JavascriptException as E:
                    logger.log(logging.WARNING, 'The javascript is not valid:' + \
                               str(E))
                    return response_text
        return response_text


class FileSourceWorker(BaseSourceWorker):
    def retrieve(self, url, kwargs):
        try:
            with open(url, **kwargs) as fle:
                return fle.read()
        except FileNotFoundError:
            logger.log(logging.WARNING, str(self.parent.name) +
                        ':File not found' + str(url) + str(kwargs))
            return False
        except Exception as E:
            logger.log(logging.WARNING, str(self.parent.name) +
                        ':Could not decode the result from ' + url)
            return False


class ProgramSourceWorker(BaseSourceWorker):
    def retrieve(self, url, kwargs):
        function = self.parent.func.format(url)
        result = subprocess.run(function, shell=True,
                                stdout=subprocess.PIPE)
        try:
            #stdout = result.stdout
            data = result.stdout.decode('utf-8')
            return data
        except Exception as E:
            logger.log(logging.WARNING, 'Could not decode the result from ' +
                        function + ':\n ' + stdout)
            return False


class ModuleSourceWorker(BaseSourceWorker):
    def retrieve(self, url, kwargs):
        """Returns the data gotten by the source

        :source: @todo
        :returns: @todo

        """
        for name in self.parent.func.split('.'):
            function = getattr(self.parent.module, name)
        try:
            data = function(url, **self.parent.kws)
            if self.conversion:
                data = self.parent.conversion(data)
            return data
        except Exception as E:
            logging.warning(' : '.join([str(E), url, str(self.parent.kws)]))
            return False


class APISourceWorker(BaseSourceWorker):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.api_function = parent.api_function
        self.batch = parent.batch

    def retrieve_batch(self, urls):
        return self.api_function(urls[0] if type(urls) == list else urls)

    def run(self):
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
