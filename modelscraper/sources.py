import os
import time
import subprocess
import urllib
import json


from selenium.common.exceptions import JavascriptException
from user_agent import generate_user_agent
import dns.resolver
import requests


from .components import BaseSource, BaseSourceWorker
from .helpers import add_other_doc


class WebSourceWorker(BaseSourceWorker):
    '''
    The Worker class for the WebSource. Largely a wrapper around the requests
    module.
    '''
    def retrieve(self, url, kwargs):
        time.sleep(self.parent.time_out)
        if self.parent.debug:
            print(self.__class__.__name__, url, kwargs)
        try:
            response = self.parent.session.request(self.parent.func, url,
                                                   **kwargs)
            if response:
                return response.text
            else:
                return False

        # Retry later with a timeout,
        except requests.Timeout:
            return False

        # Retry later with connection error.
        except requests.ConnectionError:
            # Check if the host is online or the DNS can be reached
            try:
                print('checking if the domain is up')
                parsed = urllib.parse.urlparse(url)
                dns.resolver.query(parsed.netloc)
                self.logger.warning('Retrying url' + url)
                time.sleep(self.parent.time_out)
                return False
            except dns.resolver.Timeout:
                return None

        except Exception as E:
            self.logger.exception("Error retrieving the data from: " + url)
            return None


class WebSource(BaseSource):
    '''
    A class which can make requests to webservers. It mainly wraps around the
    requests module.

    Attributes
    ----------
    kwargs :
            The keywords that can be modified for each url from values in the
            parsed object by setting the kwargs_format parameter. These are:
            "headers", "data", "form", "params", "cookies".
    '''

    kwargs = ('headers', 'data', 'form', 'params', 'cookies')
    source_worker = WebSourceWorker

    @add_other_doc(BaseSource.__init__, 'parameters')
    def __init__(self, cookies=None, data=[], domain='', form=[],
                 func='get', headers={}, json_key='', params=[],
                 session=requests.Session(), cache=False,
                 time_out=1, user_agent=True, *args, **kwargs):
        '''
        Parameters
        ----------
        cookies : dict or CookieJar, optional
                  Cookies to include with the request.

        data : list of dict, list of bytes, dict, bytes, optional
               The data that will be included for each request.
               If a list of dicts or bytes-objects is passed the
               urls and the data will be matched pairwise
               (i.e. url[i] will have data[i]).

        domain : str, optional
                 The domain parameter provides a basic way to restrain the
                 Source from making requests that are out of scope. When the
                 domain "example.com" is set, urls that do not match this
                 domain are not followed.

        func : str, optional
               The type of request that will be made for each URL.
               The types are: get, post, put, delete.

        session : requests.Session, optional
                  A requests.Session object that is used to connect to
                  the server.

                  By default, each WebSource will use it's own Session
                  object for making connections. If you want to share a
                  session to the server between WebSource objects, you can
                  provide it here. For example:

                  >>> websource = WebSource()
                  >>> other_websource = WebSource(session=websource.session)

        user_agent : bool or str, optional
                  If set to True a random UserAgent header will be added to
                  each request. If a string is provided, this string will be
                  used as a User-Agent header for each request. If set to
                  False, no UserAgent header will be added to the request.

        time_out : int, optional
                   The amount of seconds that are in between each request made
                   by a WebSourceWorker.

        cache : bool, optional
                Whether or not to using caching.
        '''
        super().__init__(*args, **kwargs)
        self.cookies = cookies
        self.data = data
        self.domain = domain
        self.form = form
        self.func = func.upper()
        self.headers = headers
        self.params = params
        self.session = session
        self.time_out = time_out
        self.user_agent = user_agent
        if cache:
            from diskcache import Cache
            self.cache = Cache('/tmp/modelscraper_cache')

    def get_kwargs(self, objct=None):
        # Get the kwargs that might be obtained from the object if passed.
        other_kwargs = super().get_kwargs(objct)

        if self.user_agent:
            if type(self.user_agent) is str:
                user_agent = self.user_agent
            else:
                user_agent = generate_user_agent(device_type=['desktop'])
            headers = {'User-Agent': user_agent}
        else:
            headers = {}

        # Add other headers from the kwargs generated by an object.
        headers = {**headers,
                   **other_kwargs.pop('headers', {})}

        # Finally setup the kwargs as a whole
        kwargs = {'headers': headers, **other_kwargs}

        # if self.func == 'post' and objct:
        #     kwargs['data'] = {attr: v[0] for attr, v in objct.items()
        #                      if attr not in ('_url', 'url')}
        return kwargs

    def add_source(self, url, attrs, objct):
        kwargs = self.get_kwargs(objct)

        if type(url) is str:
            url = self.url_template.format(url)

        prepared = requests.Request(self.func, url, **kwargs).prepare()

        if prepared.url not in self.seen:
            if self.url_regex and not self.url_regex(url):
                return False

            if self.domain:
                if self.domain not in url:
                    return False
            self.in_q.put((url, kwargs, attrs))
            self.to_parse += 1
            self.add_to_seen(url)


class BrowserSourceWorker(WebSourceWorker):
    '''Source worker for the BrowserSource. By setting the script parameter in
    the BrowserSource instance, the result of the script will be appended to
    the HTML as JSON with the root tag: "<script id='result'></script>"
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
                        script_result = '<script id="result">' + \
                            '{}<script>'.format(script_result)
                        return response_text + script_result
                except JavascriptException as E:
                    self.logger.exception('The javascript is not valid')
                    return response_text
        return response_text


class BrowserSource(WebSource):
    kwargs = ('data', 'form', 'params', 'cookies')
    source_worker = BrowserSourceWorker

    def __init__(self, browser='firefox-esr', browser_executable='',
                 script='', script_only=False, *args, **kwargs):
        self.script = script
        self.script_only = script_only

        assert browser.lower() == 'firefox-esr', \
            'Please use only firefox  as the browser, more will be added later'
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
        from seleniumrequests import Firefox as driver

        if not browser_executable:
            binary = os.popen('which ' + browser).read().strip()
        else:
            binary = browser_executable
        assert binary != '', 'The browser you chose was not ' + \
            'installed on the system'
        binary = FirefoxBinary(binary)

        options = Options()
        options.set_headless = True
        options.add_argument('--headless')

        browser = driver(firefox_binary=binary, firefox_options=options)
        super().__init__(session=browser, *args, **kwargs)

    def get_kwargs(self, objct=None):
        return super(WebSource, self).get_kwargs(objct)

    def stop(self):
        self.session.quit()
        super().stop()


class FileSourceWorker(BaseSourceWorker):
    def retrieve(self, url, kwargs):
        try:
            with open(url, **kwargs) as fle:
                return fle.read()
        except FileNotFoundError:
            self.logger.exception('File not found ' + str(url) + str(kwargs))
            return False
        except Exception as E:
            self.logger.exception('Could not decode the result from ' + url)
            return False


class FileSource(BaseSource):
    source_worker = FileSourceWorker
    kwargs = ['buffering']
    func = open
    buffering = False


class ProgramSourceWorker(BaseSourceWorker):
    def retrieve(self, url, kwargs):
        function = self.parent.func.format(url)
        result = subprocess.run(function, shell=True,
                                stdout=subprocess.PIPE)
        try:
            data = result.stdout.decode('utf-8')
            return data
        except Exception as E:
            self.logger.exception('Could not decode the result from ' +
                                  function + ':\n ' + data)
            return False


class ProgramSource(BaseSource):
    source_worker = ProgramSourceWorker


class ModuleSourceWorker(BaseSourceWorker):
    def retrieve(self, url, kwargs):
        """Returns the data gotten by the source

        :source: @todo
        :returns: @todo

        """
        for name in self.parent.func.split('.'):
            function = getattr(self.parent.module, name)
        try:
            data = function(*url)
            if self.parent.conversion:
                data = self.parent.conversion(data)
            return data
        except Exception as E:
            self.logger.exception('Could not decode the result from ' +
                                  str(url) + str(kwargs))
            return False


class ModuleSource(BaseSource):
    source_worker = ModuleSourceWorker

    """Generates data by calling another modules function."""

    def __init__(self, module=None, conversion=None, *args, **kwargs):
        """@todo: to be defined1.

        :module_name: @todo

        """
        super().__init__(*args, **kwargs)

        self.module = module
        if conversion:
            assert callable(conversion), "Please provide a callable as a " + \
                "conversion"
        self.conversion = conversion


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


class APISource(BaseSource):
    source_worker = APISourceWorker
