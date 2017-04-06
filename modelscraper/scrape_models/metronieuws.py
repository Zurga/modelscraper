from dispatcher import Dispatcher
from models.models import ScrapeModel, Run, Template, Attr, Source
from pymongo import MongoClient
from workers import WebSource
from parsers.html_parser import HTMLParser
import models

categories = {39: 'domestic',
              2: 'foreign',
              }
category_url = "http://www.metronieuws.nl/getsectionlist/{}/{}/0"

sources = (Source(url=category_url.format(cat_id, i), json_key=['data'],
                  attrs=[Attr(name='category', value=cat_name)])
        for cat_id, cat_name in categories.items() for i in range(1, 10000))

metro = ScrapeModel(
    name='metronieuws.nl', domain='http://metronieuws.nl',
    runs=[
        Run(source_worker=WebSource, parser=HTMLParser, sources=sources,
            templates=[
                Template(
                    name='headline', selector='.row', db='metronieuws', db_type='mongo_db',
                    table='headlines', required=True, attrs=[
                        Attr(name='url', selector='a.shadow-block',
                             func='sel_attr', kws={'attr': 'href'},
                             source=Source(active=False)),
                        Attr(name='title', selector='h3', func='sel_text'),
                        Attr(name='excerpt', selector='div > p', func='sel_text'),
                        Attr(name='date', selector='div.wrapper.small div:nth-of-type(1)',
                                    func='sel_text'),
                        Attr(name='num_reactions', selector='div.amount', func='sel_text'),
                    ]
                )
            ]),
        Run(templates=[
            Template(
                name='article', selector='.artikel', db='metronieuws',
                table='articles', db_type='mongo_db', attrs=[
                    Attr(name='title', selector='h1', func='sel_text'),
                    Attr(name='author', selector='.username', func='sel_text'),
                    Attr(name='date', func='sel_attr', kws={'attr':'content'},
                         selector='.small span[datatype="xsd:dateTime"]'),
                    Attr(name='text', func='sel_text',
                         selector='.content .field-items .field-item > p'),
                    Attr(name='related', func='sel_url',
                         selector='h2 + div > .col-1 a')
                ])
        ])
    ])

disp = Dispatcher()
disp.add_scraper(metro)
disp.run()
