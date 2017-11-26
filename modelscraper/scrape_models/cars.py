from dispatcher import Dispatcher
import re
import models
from functions.store_functions import *
from functions.parse_functions import *
from pymongo import MongoClient

client = MongoClient()

autoscout = ScrapeModel(name='autoscout24', domain='autoscout24.nl', phases=[
    Phase(getters=[models.Getter(url='http://ww4.autoscout24.nl/?atype=B&mmvco=0&cy=NL&ustate=N%2CU&fromhome=1&intcidm=HP-Searchmask-Button&dtr=s&results=20')],
        templates=[
            Template(name='motorcycle', js_regex='var articlesFromServer = (.+)\|\|', attrs=[
                Attr(name='price', func=sel_json, kws={'key': 'price_raw'}),
                Attr(name='brand', func=sel_json, kws={'key': 'mk'}),
                Attr(name='make', func=sel_json, kws={'key': 'md'}),
                Attr(name='year', func=sel_json, kws={'key': 'fr'}),
                Attr(name='mileage', func=sel_json, kws={'key': 'ma'}),
                Attr(name='city', func=sel_json, kws={'key': 'ct'}),
                Attr(name='url', func=sel_json, kws={'key': 'ei'}),
                Attr(name='zip', func=sel_json, kws={'key': 'zp'}),
                Attr(name='power', func=sel_json, kws={'key': 'pk'}),
            ], store=StoreObject(func=store_mongo,
                                        kws={'db': 'moto_final', 'collection': 'auto24'})
            )
        ]
        )
])

autotrader = ScrapeModel(name='autotrader', domain='http://autotrader.nl', num_getters=1, cookies={'CookieOptIn': 'true'},
                          phases=[
    Phase(
        getters=[
            Getter(url='http://www.autotrader.nl/motor/zoeken/'),
        ],
        templates=[
            Template(name='motorcycle', selector='.result',
                            store=StoreObject(func=store_mongo,
                                                     kws={'db': 'moto', 'collection': 'autotrader'}),
                       attrs=[
                           Attr(name='brand', selector='h2', func=sel_text,
                                       kws={'regex': '(^\w+)'}),
                           Attr(name='name', selector='h2', func=sel_text,
                                       kws={'regex': '^\w+ (.*)'}),
                           Attr(name='price', selector='.result-price-label', func=sel_text,
                                       kws={'numbers': 1}),
                           Attr(name='year', selector='.col-left',
                                       func=sel_text, kws={'regex': '\w{3} (\d{4})', 'numbers': 1}),
                           Attr(name='mileage', selector='.col-left',
                                       func=sel_text, kws={'regex': '(.*) km', 'numbers': 1}),
                           Attr(name='url', selector='a.tracker', func=sel_attr,
                                       kws={'attr': 'href'}),
                           Attr(name='dealer_name', selector='.dealer-info div', func=sel_text),
                       ]),
            Template(name='next_page', selector='#pager', attrs=[
                Attr(name='url', func=sel_attr, selector='a.tracker',
                            kws={'attr': 'href'}, getter=Getter()),
            ]),
        ]
        )
])

marktplaats = ScrapeModel(name='marktplaats', domain='marktplaats.nl', num_getters=2, cookies={'CookieOptIn': 'true'},
                          phases=[
    Phase(
        getters=[
            Getter(url='http://www.marktplaats.nl/z/auto-s/volkswagen.html?categoryId=157',
               attrs=[Attr(name='brand', value='Volkswagen')]),
    ],
        templates=[
            Template(name='marktplaats_automobile', selector='section.search-results-table article',
                            store=StoreObject(func=store_mongo,
                                                     kws={'db': 'cars', 'collection': 'cars'}),
                       attrs=[
                           Attr(name='name', selector='h2 a', func=sel_text,
                                       kws={'regex': '(\w+) -,'}),
                           Attr(name='price', selector='.price', func=sel_text,
                                       kws={'regex': '(\d+),', 'numbers': 1}),
                           Attr(name='year', selector='.listing-priority-product-container',
                                       func=sel_text, kws={'regex': '(\d{4})', 'numbers': 1}),
                           Attr(name='mileage', selector='.listing-priority-product-container',
                                       func=sel_text, kws={'regex': '(.*) km', 'numbers': 1}),
                           Attr(name='city', func=sel_text, selector='.location-name'),
                           Attr(name='url', selector='h2 > a', func=sel_attr, kws={'attr': 'href'}),
                       ]),
            Template(name='pages', selector='#pagination-pages', attrs=[
                Attr(name='url', func=sel_attr, selector='a',
                            kws={'attr': 'href'}, getter=Getter()),
            ]),
        ]
        )
])

bikenet = ScrapeModel(name='bikenet', domain='bikenet.nl', num_get=1, phases=[
    Phase(
        getters=[Getter(url='https://bikenet.nl/occasions/?occasionsPerPage=90&pagina=1')],
        templates=[
        Template(name='motorcycle', selector='li.span3',
                        store=StoreObject(func=store_mongo, kws={'db': 'moto', 'collection': 'bikenet'}),
                   attrs=[
                       Attr(name='price', selector='.unitPrice', func=sel_text, kws={'replacers': ['€ ', '\.', ',-'], 'numbers': 1}),
                       Attr(name='brand', selector='.caption .h5', func=sel_text),
                       Attr(name='make', selector='.caption .h6', func=sel_text),
                       Attr(name='year', selector='.unitInfo', func=sel_text,
                                   kws={'regex': 'Model: (\d+)', 'numbers': 1}),
                       Attr(name='mileage', selector='.unitInfo', func=sel_text,
                                   kws={'regex': 'KM Stand: (\d+)', 'numbers': 1}),
                       Attr(name='url', selector='.unitLink', func=sel_attr, kws={'attr': 'href'}),
                ]),
            Template(name='next_page', attrs=[
                Attr(name='url', selector='.pagination.bottom a[href*="pagina"]',
                            func=sel_attr, kws={'attr': 'href'}, getter=Getter())
            ])
        ])
    ])


disp = Dispatcher()
disp.add_scraper(marktplaats)
# disp.add_scraper(bikenet)
# disp.add_scraper(autotrader)
# disp.add_scraper(autoscout)
disp.run()
