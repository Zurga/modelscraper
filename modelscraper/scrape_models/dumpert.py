from parse_functions import *  # noqa
from store_functions import *  # noqa
from lxml.cssselect import CSSSelector as css
from dispatcher import Dispatcher
import json

dumpert_class = [
    {'name': 'Dumpert',
     'domain': 'http://dumpert.nl',
     'num_get': 1,
     'runs': [
         {'to_getter': [{'url': 'http://dumpert.nl/{}/'.format(i if i else ''),
                         'active': 1} for i in range(2)],
          'to_parser': {
              'object_types': {
                  'upload': {
                      'pre_selector': css('a.dumpthumb'),
                      'to_store': {'func': store_json,
                                   'kwargs': {'filename': 'dumpert',}
                                   },
                      'attrs': {
                          'url': {
                              'func': sel_attr,
                              'kwargs': {
                                  'attr': 'href',}
                          },
                          'title': {
                              'func': sel_text,
                              'kwargs': {
                                  'selector': css('.details h1'),
                              },
                          },
                          'date': {
                              'func': sel_text,
                              'kwargs': {
                                  'selector': css('.details date'),
                              },
                          },
                          'views': {
                              'func': sel_regex,
                              'kwargs': {
                                  'selector': css('p.stats'),
                                  'regex': 'views: (\d+)',
                              },
                          },
                          'kudos': {
                              'func': sel_regex,
                              'kwargs': {
                                  'selector': css('p.stats'),
                                  'regex': 'kudos: (\d+)',
                              },
                          },
                          'description': {
                              'func': sel_text,
                              'kwargs': {
                                  'selector': css('.description'),
                              },
                          },
                      }
                  }
              }
          }
          }
        ]
    }
]

dispatcher = Dispatcher(classes=dumpert_class)
results = dispatcher.run()
