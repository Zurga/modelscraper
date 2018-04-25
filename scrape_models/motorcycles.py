import re
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from modelscraper.parsers import JSONParser


vehicle_type = Attr(name='vehicle_type')
price = Attr(name='price', func='sel_text', kws={'numbers': True}, type=int)
brand = Attr(name='brand', func='sel_text')
make = Attr(name='make', func='sel_text')
year = Attr(name='year', func='sel_text', kws={'numbers': True}, type=int)
mileage = Attr(name='mileage', func='sel_text', kw={'numbers': True}, type=int)
city = Attr(name='city', func='sel_text')
url = Attr(name='url', func='sel_url')
zipcode = Attr(name='zip', func='sel_text')
power = Attr(name='power', func='sel_text')

vehicle = Template(
    name='vehicle', db_type='MongoDB', db='vehicles',
    attrs=[
        vehicle_type,
        price,
        brand,
        make,
        year,
        mileage,
        city,
        url,
        zipcode,
        power
    ]
)

autoscout_template = vehicle(
    table='autoscout', regex='var articlesFromServer = (.+)\|\|',
    attrs=[
        vehicle_type,
        price(selector='price_raw'),
        brand(selector='mk'),
        make(selector='md'),
        year(selector='fr'),
        mileage(selector='ma'),
        city(selector='ct'),
        url(selector='ei', func='sel_text'),
        zipcode(selector='zp'),
        power(selector='pk')
    ]
)

autotrader_template = vehicle(
    table='autotrader', selector='.result',
    attrs=[
        brand(selector='h2', kws={'regex': '(^\w+)'}),
        make(selector='h2', kws={'regex': '^\w+ (.*)'}),
        price(selector='.result-price-label'),
        year(selector='.col-left',kws={'regex': '\w{3} (\d{4})'}),
        mileage(selector='.col-left', kws={'regex': '(.*) km'}),
        url(selector='a.tracker'),
        #Attr(name='dealer_name', selector='.dealer-info div', func=sel_text),
        city,
        zipcode,
        power,
    ])
sources = models.Source(url='http://ww4.autoscout24.nl/?atype=B&mmvco=0&cy=NL&ustate=N%2CU&fromhome=1&intcidm=HP-Searchmask-Button&dtr=s&results=20')

marktplaats_template = Template(
    name='motorcycle', selector='section.search-results-table article',
    table='marktplaats',
    attrs=[
        make(selector='h2 a', kws={'regex': '(\w+) -,'}),
        price(selector='.price', kws={'regex': '(\d+),'}),
        year(selector='.listing-priority-product-container',
             kws={'regex': '(\d{4})'}),
        mileage(selector='.listing-priority-product-container',
                    kws={'regex': '(.*) km'}),
        city(selector='.location-name'),
        url(selector='h2 > a'),
    ]
)
autoscout = ScrapeModel(
    name='autoscout24',
    domain='autoscout24.nl',
    phases=[
        Phase(sources=[], templates=[autoscout_template]),
])

autotrader = ScrapeModel(name='autotrader', domain='http://autotrader.nl', num_sources=1, cookies={'CookieOptIn': 'true'},
                          phases=[
    Phase(
        sources=[
            Source(url='http://www.autotrader.nl/motor/zoeken/'),
        ],
        templates=[
            Template(name='motorcycle', selector='.result',
                            store=StoreObject(func=store_mongo,
                                                     kws={'db': 'moto', 'collection': 'autotrader'}),
                       attrs=[
                       ]),
            Template(name='next_page', selector='#pager', attrs=[
                Attr(name='url', func=sel_attr, selector='a.tracker',
                            kws={'attr': 'href'}, getter=Source()),
            ]),
        ]
        )
])

marktplaats = ScrapeModel(
    name='marktplaats', domain='marktplaats.nl', num_sources=2, cookies={'CookieOptIn': 'true'},
    phases=[
        Phase(
            sources=[
        Source(url='http://www.marktplaats.nl/z/motoren/motoren-bmw.html?categoryId=692',
               attrs=[brand(value='BMW')]),
        Source(url='http://www.marktplaats.nl/z/motoren/motoren-kawasaki.html?categoryId=697',
               attrs=[brand(value='Kawasaki')]),
        Source(url='http://www.marktplaats.nl/z/motoren/motoren-honda.html?categoryId=696',
               attrs=[brand(value='Honda')]),
        Source(url='http://www.marktplaats.nl/z/motoren/motoren-suzuki.html?categoryId=707',
               attrs=[brand(value='SUZUKI')]),
        Source(url='http://www.marktplaats.nl/z/motoren/motoren-yamaha.html?categoryId=710',
               attrs=[brand(value='Yamaha')]),
        Source(url='http://www.marktplaats.nl/z/motoren/motoren-triumph.html?categoryId=709',
               attrs=[brand(value='Triumph')]),
    ],
        templates=[
            marktplaats_template,
            Template(name='pages', selector='#pagination-pages', attrs=[
                Attr(name='url', func=sel_attr, selector='a',
                            kws={'attr': 'href'}, getter=Source()),
            ]),
        ]
        )
])

bikenet = ScrapeModel(name='bikenet', domain='bikenet.nl', num_get=1, phases=[
    Phase(
        sources=[Source(url='https://bikenet.nl/occasions/?occasionsPerPage=90&pagina=1')],
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
                            func=sel_attr, kws={'attr': 'href'}, getter=Source())
            ])
        ])
    ])
