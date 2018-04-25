import re
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from modelscraper.parsers import JSONParser
import vehicle


city = Attr(name='city', func='sel_text')
zipcode = Attr(name='zipcode', func='sel_text')

occasion = Template(
    name='occasion', db_type='mongo_db',
    attrs=[*vehicle.attrs,
        city,
        zipcode,
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
'''
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
'''
