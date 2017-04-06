from scraper import Scraper
import json
from parse_functions import *  # noqa
from store_functions import *  # noqa
from lxml.cssselect import CSSSelector as css
from queue import Queue
from threading import Thread
from dispatcher import Dispatcher
import time
import sys

clss = [
        {
        'name': 'mediamarkt',
        'domain': 'http://www.mediamarkt.nl',
        'runs': [
            {
            'to_getter': [
                {'url': 'http://www.mediamarkt.nl/',
                'active': 1,
                },
                ],
            'to_parser': {
                'object_types': {
                    'link': {
                        'pre_selector': css('#top-navigation'),
                        'attrs': {
                            'menu_item': {
                                'func': sel_attr,
                                'kwargs': {
                                    'selector': css('li.item a'),
                                    'index': 0,
                                    'attr': 'href'},
                                'follow': {'forward': 1},
                                },
                            },
                        },
                    }
                },
            },
            {'to_parser': {
                'object_types': {
                    'link': {
                       'pre_selector': css('ul.categories-flat-descendants'),
                       'attrs': {
                        'submenu': {
                            'func': sel_attr,
                            'kwargs': {
                                'selector': css('li.child-active ul a'),
                                'attr': 'href'
                            },
                            'follow': {'forward': 1},
                            },
                            },
                       }
                   }
                },
            },
            {'to_parser': {
                'object_types': {
                    'next_page': {
                        'attrs': {
                            'next_link': {
                                'func': sel_attr,
                                'kwargs': {
                                    'selector': css('li.pagination-next a'),
                                    'index': 0,
                                    'attr': 'href'},
                                    },
                                'follow': 1,
                            }
                        },
                    'product': {
                        'pre_selector': css('.product-wrapper'),
                        'to_store': {'func': store_json,
                                     'kwargs': {
                                         'filename': 'mediamarkt.json',
                                     },
                                     },
                        'attrs': {
                            'price': {
                                'func': sel_text,
                                'kwargs': {
                                    'selector': css('.price'),
                                    },
                                },
                            'name': {
                                'func': sel_text,
                                'kwargs': {
                                    'selector': css('h2 a')
                                        }
                                },
                            'available': {
                                'func': sel_regex,
                                'kwargs': {
                                        'selector': css('div.availability'),
                                        'regex': 'Voor .'
                                    },
                                },
                            'url': {
                                'func': sel_attr,
                                'kwargs': {
                                    'selector': css('h2 a'),
                                    'attr': 'href'},
                                },
                            },
                        }
                    }
                }
            }
        ],
    },
]

'''
        {
        'name': 'cameranu',
        'domain': 'http://www.cameranu.nl',
        'runs': [
            {'to_getter': [{ 'url': 'http://cameranu.nl', 'active': 1, },
                           ],
             'to_parser': {
                'object_types': {
                    'menu': {
                        'pre_selector': css('.product'),
                        'attrs': {
                            'link': {
                                'follow': {'forward': 1},
                                'func': sel_text,
                                'kwargs': {
                                    'selector': css('.catalog-price > p'),
                                    'attr': 'href',
                                },
                                },
                            }
                        }
                    }
                },
             },
            {'to_parser': {
                'object_types': {
                    'next_page': {
                        'attrs': {
                            'link': {
                                'func': sel_attr,
                                'kwargs': {
                                    'selector': css('li.pagination-next a'),
                                    'attr': 'href',
                                },
                            'follow': 1,
                            },
                        },
                    },
                    'product': {
                        'pre_selector': css('.product'),
                        'to_store': {'func': store_json,
                                     'kwargs': {
                                         'filename': 'mediamarkt.json',
                                     },
                        'attrs':{
                            'price': {'func': sel_text,
                                    'kwargs': {
                                        'selector': css('.catalog-price > p'),
                                    },
                                    },
                            'name': {'func': sel_text,
                                    'kwargs': {
                                        'selector': css('.product-title')
                                    }
                                    },
                            'available': {'func': sel_regex,
                                        'kwargs': {
                                            'selector': css('div.catalog-labels'),
                                            'regex': 'Direct .'
                                        },
                                        },
                            'url': {'func': sel_attr,
                                    'kwargs': {
                                        'selector': css('.product-title'),
                                        'attr': 'href'},
                                    },
                        },
                    }
                }
                }
            }
            }
        ],
        }

            {'url_suffixes': [
                    {'url': '/nl/spiegelreflexcamera',
                    'active': 0,
                    },
                    {'url': '/nl/search?sort=relevance&q=camera&show=20',
                    'active': 1,
                    },
                    {'url': '/nl/search?sort=relevance&q=objectief&show=20',
                    'active': 1,
                    },
                    {'url': '/nl/search?sort=relevance&q=&show=20',
                    'active': 1,
                    },
                    {'url': '/nl/search?sort=relevance&q=nikon&show=20',
                    'active': 1,
                    },
                    {'url': '/nl/search?sort=relevance&q=nikon&show=20',
                    'active': 1,
                    },
                    {'url': '/nl/search?sort=relevance&q=nikon&show=20',
                    'active': 1,
                    },
                    {'url': '/nl/search?sort=relevance&q=nikon&show=20',
                    'active': 1,
                    },
                ],
'''
disp = Dispatcher(classes=clss)
disp.run()
