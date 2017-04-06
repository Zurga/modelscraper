from scraper import ListScraper
from parse_functions import *  # noqa
from lxml.cssselect import CSSSelector as css
import time

clss = {
    'mediamarkt': {
        'start': [
            {'url': '/scholenoverzicht/vo/',
             'active': 1,
             },
        ],
        'list_url': 'http://www.onderwijsconsument.nl',
        'object_url': 'http://www.onderwijsconsument.nl',
        # 'iter_class': css('li.pagination-next a'),
        'css': {
            'list_class': css('#lijst .school a'),
            'sections': {
                'school': {
                    'selector': css('#school'),
                    'css':{
                        'onderwijs': {'func': sel_text,
                                'params': {
                                    'selector': css('.lead'),
                                },
                                },
                        'name': {'func': sel_text,
                                'params': {
                                    'selector': css('h2')
                                }
                                },
                        'email': {'func': sel_attr,
                                'params': {
                                    'selector': css('#sidebar a:nth-of-type(2):not([target="_blank"])'),
                                    'attr': 'href'},
                                },
                    },
                }
            }
        }
    },
}

scraper = ListScraper(clss)
start = time.time()
results = scraper.start_scraping()
print(results)
