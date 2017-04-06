from dispatcher import Dispatcher
import re
import models
from functions.store_functions import *
from functions.parse_functions import *
from pymongo import MongoClient

client = MongoClient()

autoscout = models.ScrapeModel(name='autoscout24', domain='autoscout24.nl', runs=[
    models.Run(getters=[models.Getter(url='http://ww4.autoscout24.nl/?atype=B&mmvco=0&cy=NL&ustate=N%2CU&fromhome=1&intcidm=HP-Searchmask-Button&dtr=s&results=20')],
        templates=[
            models.Template(name='motorcycle', js_regex='var articlesFromServer = (.+)\|\|', attrs=[
                models.Attr(name='price', func=sel_json, kws={'key': 'price_raw'}),
                models.Attr(name='brand', func=sel_json, kws={'key': 'mk'}),
                models.Attr(name='make', func=sel_json, kws={'key': 'md'}),
                models.Attr(name='year', func=sel_json, kws={'key': 'fr'}),
                models.Attr(name='mileage', func=sel_json, kws={'key': 'ma'}),
                models.Attr(name='city', func=sel_json, kws={'key': 'ct'}),
                models.Attr(name='url', func=sel_json, kws={'key': 'ei'}),
                models.Attr(name='zip', func=sel_json, kws={'key': 'zp'}),
                models.Attr(name='power', func=sel_json, kws={'key': 'pk'}),
            ], store=models.StoreObject(func=store_mongo,
                                        kws={'db': 'moto_final', 'collection': 'auto24'})
            )
        ]
        )
])

autotrader = models.ScrapeModel(name='autotrader', domain='http://autotrader.nl', num_getters=1, cookies={'CookieOptIn': 'true'},
                          runs=[
    models.Run(
        getters=[
            models.Getter(url='http://www.autotrader.nl/motor/zoeken/'),
        ],
        templates=[
            models.Template(name='motorcycle', selector='.result',
                            store=models.StoreObject(func=store_mongo,
                                                     kws={'db': 'moto', 'collection': 'autotrader'}),
                       attrs=[
                           models.Attr(name='brand', selector='h2', func=sel_text,
                                       kws={'regex': '(^\w+)'}),
                           models.Attr(name='name', selector='h2', func=sel_text,
                                       kws={'regex': '^\w+ (.*)'}),
                           models.Attr(name='price', selector='.result-price-label', func=sel_text,
                                       kws={'numbers': 1}),
                           models.Attr(name='year', selector='.col-left',
                                       func=sel_text, kws={'regex': '\w{3} (\d{4})', 'numbers': 1}),
                           models.Attr(name='mileage', selector='.col-left',
                                       func=sel_text, kws={'regex': '(.*) km', 'numbers': 1}),
                           models.Attr(name='url', selector='a.tracker', func=sel_attr,
                                       kws={'attr': 'href'}),
                           models.Attr(name='dealer_name', selector='.dealer-info div', func=sel_text),
                       ]),
            models.Template(name='next_page', selector='#pager', attrs=[
                models.Attr(name='url', func=sel_attr, selector='a.tracker',
                            kws={'attr': 'href'}, getter=models.Getter()),
            ]),
        ]
        )
])

marktplaats = models.ScrapeModel(name='marktplaats', domain='marktplaats.nl', num_getters=2, cookies={'CookieOptIn': 'true'},
                          runs=[
    models.Run(
        getters=[
            models.Getter(url='http://www.marktplaats.nl/z/auto-s/volkswagen.html?categoryId=157',
               attrs=[models.Attr(name='brand', value='Volkswagen')]),
    ],
        templates=[
            models.Template(name='marktplaats_automobile', selector='section.search-results-table article',
                            store=models.StoreObject(func=store_mongo,
                                                     kws={'db': 'cars', 'collection': 'cars'}),
                       attrs=[
                           models.Attr(name='name', selector='h2 a', func=sel_text,
                                       kws={'regex': '(\w+) -,'}),
                           models.Attr(name='price', selector='.price', func=sel_text,
                                       kws={'regex': '(\d+),', 'numbers': 1}),
                           models.Attr(name='year', selector='.listing-priority-product-container',
                                       func=sel_text, kws={'regex': '(\d{4})', 'numbers': 1}),
                           models.Attr(name='mileage', selector='.listing-priority-product-container',
                                       func=sel_text, kws={'regex': '(.*) km', 'numbers': 1}),
                           models.Attr(name='city', func=sel_text, selector='.location-name'),
                           models.Attr(name='url', selector='h2 > a', func=sel_attr, kws={'attr': 'href'}),
                       ]),
            models.Template(name='pages', selector='#pagination-pages', attrs=[
                models.Attr(name='url', func=sel_attr, selector='a',
                            kws={'attr': 'href'}, getter=models.Getter()),
            ]),
        ]
        )
])

bikenet = models.ScrapeModel(name='bikenet', domain='bikenet.nl', num_get=1, runs=[
    models.Run(
        getters=[models.Getter(url='https://bikenet.nl/occasions/?occasionsPerPage=90&pagina=1')],
        templates=[
        models.Template(name='motorcycle', selector='li.span3',
                        store=models.StoreObject(func=store_mongo, kws={'db': 'moto', 'collection': 'bikenet'}),
                   attrs=[
                       models.Attr(name='price', selector='.unitPrice', func=sel_text, kws={'replacers': ['€ ', '\.', ',-'], 'numbers': 1}),
                       models.Attr(name='brand', selector='.caption .h5', func=sel_text),
                       models.Attr(name='make', selector='.caption .h6', func=sel_text),
                       models.Attr(name='year', selector='.unitInfo', func=sel_text,
                                   kws={'regex': 'Model: (\d+)', 'numbers': 1}),
                       models.Attr(name='mileage', selector='.unitInfo', func=sel_text,
                                   kws={'regex': 'KM Stand: (\d+)', 'numbers': 1}),
                       models.Attr(name='url', selector='.unitLink', func=sel_attr, kws={'attr': 'href'}),
                ]),
            models.Template(name='next_page', attrs=[
                models.Attr(name='url', selector='.pagination.bottom a[href*="pagina"]',
                            func=sel_attr, kws={'attr': 'href'}, getter=models.Getter())
            ])
        ])
    ])


disp = Dispatcher()
disp.add_scraper(marktplaats)
# disp.add_scraper(bikenet)
# disp.add_scraper(autotrader)
# disp.add_scraper(autoscout)
disp.run()
