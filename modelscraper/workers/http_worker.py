from threading import Thread
from queue import Queue
import time
from user_agent import generate_user_agent
import requests


class WebSource(Thread):
    '''
    This class is used as a downloader for pages.
    It will place all items in its queue into the out_q specified.
    For use without parent Thread supply keyword arguments: name, domain, in_q,
    '''
    def __init__(self, parent=None, id=0, out_q=Queue(), time_out=0.3, retries=10, **kwargs):
        super(WebSource, self).__init__()
        if parent or kwargs and out_q:
            self.name = parent.name + str(id) + 'WebSource'
            self.domain = parent.domain
            self.in_q = parent.source_q
            self.out_q = parent.parse_q
            self.retries = retries
            self.session = parent.session
            self.user_agent = parent.user_agent
            self.time_out = time_out
            self.times = []
            self.visited = 0
            self.last_mean = 0
            self.to_parse = parent.to_parse

        else:
            raise Exception('Not enough specified, read the docstring.')

        for key, value in kwargs.items():
            setattr(self, key, value)
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
                # self.visited += 1
                # self.times.append(page.elapsed.total_seconds())
                # TODO fix means calculation for automatic worker scaling.
                '''
                if self.visited % 50 == 0:
                    self.last_mean = mean(times)
                    self.times = []
                    new_mean = mean(times)
                    if abs(new_mean - self.last_mean) > 0.10:
                '''
                # print(id(self), '{}'.format(source.url), page, source.method, source.data)

                if page and source.parse:
                    source.data = page.text
                    self.out_q.put(source)
                else:
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
