import requests as req
import json
from lxml.cssselect import CSSSelector as css
from parse_functions import *  # noqa
from store_functions import *  # noqa
from dispatcher import Dispatcher

neighborhoods = [
    'Oost',
    'Oud-Zuid',
    'Oud-West',
    'Bos+en+Lommer',
    'Buiksloterham',
    'Buikslotermeer',
    'De+Pijp',
    'De+Wallen',
    'Grachtengordel',
    'Hoofddorppleinbuurt',
    'Indische+Buurt',
    'Jordaan',
    'Museumkwartier',
    'Nieuwendammerham',
    'Nieuwmarkt+en+Lastage',
    'Oostelijke+Eilanden+en+Kadijken',
    'Oosterparkbuurt',
    'Osdorp',
    'Overtoomse+Veld',
    'Rivierenbuurt',
    'Slotervaart',
    'Spaarndammer+en+Zeeheldenbuurt',
    'Stadionbuurt',
    'Volewijck',
    'Watergraafsmeer',
    'Westelijke+Eilanden',
    'Zeeburg',
    ]
'''
     'login': {'url': 'https://www.airbnb.com/authenticate',
               'kwargs': {
                   'params': {
                       'email': 'jamesbender@mailinator.com',
                       'password': 'socialehuur!'}
               },
               },
'''
session = req.Session()
clss = [
    {'name': 'airbnb',
     'domain': 'http://airbnb.com/',
     'time_out': 0.5,
     'num_get': 30,
     'phases': [
         {'to_getter': [{'url': 'https://www.airbnb.com/s/amsterdam--netherlands',
                         'kwargs': {
                             'params': {'guests':5,
                                        'checkin': '05%2F01%2F2017',
                                        'checkout': '05%2F05%2F2017',
                                        'neighborhoods[]': '%s' % (hood),
                                        }
                         },
                         'active': 1} for hood in neighborhoods],
          'to_parser': {
              'raw_html': False,
              'object_types': {
                  'next_page': {
                      'objects': {
                          'next_page': {
                              'parse_func': sel_attr,
                              'kwargs': {
                                  'attr': 'href',
                                  'selector': css('.next_page a'),
                              },
                              'follow': 1,
                          },
                      },
                  },
                  'airbnb_listing': {
                      'pre_selector': css('.listing'),
                      'objects': {
                          'url': {
                              'parse_func': sel_attr,
                              'kwargs': {
                                  'attr': 'data-url',
                              },
                          },
                          'reviews': {
                              'parse_func': sel_attr,
                              'kwargs': {
                                  'attr': 'data-review-count',
                              },
                          },
                          'name': {
                              'parse_func': sel_attr,
                              'kwargs': {
                                  'attr': 'data-name',
                              },
                          },
                          'lat': {
                              'parse_func': sel_attr,
                              'kwargs': {
                                  'attr': 'data-lat',
                              },
                          },
                          'lng': {
                              'parse_func': sel_attr,
                              'kwargs': {
                                  'attr': 'data-lng',
                              },
                          },
                    },
                },
              },
            },
          },
        ]
    }
]

disp = Dispatcher(classes=clss)
results = disp.run()
filename = input('filename:')
with open(filename, 'w') as fle:
    json.dump(results, fle)
