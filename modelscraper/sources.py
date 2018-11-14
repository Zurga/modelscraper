from collections import defaultdict
import logging
import os

import requests
from user_agent import generate_user_agent

from .components import Source
from .helpers import str_as_tuple
from .source_workers import WebSourceWorker, FileSourceWorker, \
    ProgramSourceWorker, ModuleSourceWorker, APISourceWorker, \
    BrowserSourceWorker



class WebSource(Source):
    kwargs = ('headers', 'data', 'form', 'params', 'cookies')
    source_worker = WebSourceWorker

    def __init__(self, cookies=None, data=[], domain='', form=[],
                 func='get', headers={}, json_key='', params=[],
                 retries=10, session=requests.Session(),
                 time_out=1, user_agent='', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cookies = cookies
        self.data = data
        self.domain = domain
        self.form = form
        self.headers = headers
        self.json_key = json_key
        self.params = params
        self.retries = retries
        self.session = session
        self.time_out = time_out
        self.user_agent = user_agent
        self.func = func

    def get_kwargs(self, objct=None):
        if not self.user_agent:
            user_agent = generate_user_agent(device_type=['desktop'])
        else:
            user_agent = self.user_agent
        other_kwargs = super().get_kwargs(objct)
        kwargs = {
            'headers': {
                'User-Agent': user_agent
            }, **other_kwargs}
        if self.func == 'post' and objct:
            kwargs['data'] = {attr: v[0] for attr, v in objct.items()
                                if attr not in ('_url', 'url')}
        return kwargs

    def add_source(self, url, attrs, objct):
        if self.domain:
            if self.domain in url:
                super().add_source(url, attrs, objct)
        else:
            super().add_source(url, attrs, objct)

class BrowserSource(WebSource):
    kwargs = ('data', 'form', 'params', 'cookies')
    source_worker = BrowserSourceWorker
    def __init__(self, browser='firefox-esr', browser_executable='',
                 script='', script_only=False, *args, **kwargs):
        self.script = script
        self.script_only=script_only

        assert browser.lower() == 'firefox-esr', \
            'Please use only firefox  as the browser, more will be added later'
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
        from seleniumrequests import Firefox as driver

        if not browser_executable:
            binary = os.popen('which ' + browser).read().strip()
        else:
            binary = browser_executable
        assert binary != '', 'The browser you chose was not installed on the system'
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

class FileSource(Source):
    source_worker = FileSourceWorker
    kwargs = ['buffering']
    func = open
    buffering = False

class ProgramSource(Source):
    source_worker = ProgramSourceWorker

class ModuleSource(Source):
    source_worker = ModuleSourceWorker

    """Generates data by calling another modules function."""

    def __init__(self, module=None, conversion=None, *args, **kwargs):
        """@todo: to be defined1.

        :module_name: @todo

        """
        super().__init__(*args, **kwargs)

        self.module = module
        self.conversion = conversion

class APISource(Source):
    source_worker = APISourceWorker
