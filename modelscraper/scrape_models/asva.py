from scraper import ListScraper
import json
from parse_functions import *  # noqa
from lxml.cssselect import CSSSelector as css
from queue import Queue
from threading import Thread
import time
import sys

clss = [
    {'name': 'asva',
     'domain': 'http://asva.nl/',
     'runs': [
         {'starts': [
             {'url': 'http://asva.nl/',
              'active': 1,
              },
            ],
         'css': {
             'list' : {'css': {
                       'menu': {'func': sel_attr,
                                 'params': {
                                     'selector': css('li a'),
                                     'attr': 'href'},
                                 'follow': 1,
                                 'store': 0,
                                 'forward': 1,
                                 },
                        },
                       'selector': css('ul.menu'),
                       }
            },
         },
         {'starts': [],
          'css': {
              'page_link': {
                  'css': {
                      'links': {
                          'func': sel_attr,
                          'params': {
                              'selector': css('.content a'),
                              'attr': 'href'},
                          'follow': 1,
                          'cross_domain': 0,
                      },
                      'page': {
                          'func': sel_text,
                          'params': {
                              'selector': css('article'),
                            },
                        },
                    }
                },
            }
          }
        ]
     }
]


scrapers = []
results = []
store_q = Queue()

def store_object():
    while True:
        item = store_q.get()
        if item is None:
            break
        to_store = item
        results.append(to_store)
        # print('got %d object(s) already' % (len(self.results)))
        store_q.task_done()
store_thread = Thread(target=store_object)
store_thread.start()

for cl in clss:
    scraper = ListScraper(**cl, output_q=store_q)  # noqa
    scraper.daemon = True
    scrapers.append(scraper)
    scraper.start()

start_time = time.time()
for scraper in scrapers:
    scraper.join()

store_q.join()
store_q.put(None)
print(len(results))
print('took: ', time.time() - start_time)
with open('asva.json', 'w') as fle:
    json.dump(results, fle)
