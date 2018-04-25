from dispatcher import Dispatcher
import models
from workers import WebSource
from parsers import HTMLParser
import string
from pymongo import MongoClient
import operator as op


fuelly = ScrapeModel(
    name='fuelly', domain='http://www.fuelly.com', num_getters=1, phases=[
    Phase(source_worker=WebSource, parser=HTMLParser, sources=(
        Source(url="http://www.fuelly.com/motorcycle"),),
        templates=[
            Template(
                name='motorcycle_link', selector='.list li',
                attrs=[
                    Attr(name='amount',func='sel_text', kws={'regex': '\((\d+)\)',
                                                                    'debug': True,
                                                                    }),
                    Attr(name='url', selector='a',
                                func='sel_url', source={'active': False},
                                source_condition={'amount': '> 2'}),
                ]
            )]
    ),
    Phase(source_worker=WebSource, parser=HTMLParser,
        templates=[
            Template(
                name='motorcycle', selector='.model-year-item',
                db_type='MongoDB', db='fuelly', table='motorcycles',
                attrs=[
                    Attr(name='name', selector='.summary-view-all-link a',
                                func='sel_text'),
                    Attr(name='url', selector='.summary-view-all-link a',
                                func='sel_url'),
                    Attr(name='year', selector='.summary-year',
                                func='sel_text', kws={'numbers': True}),
                    Attr(name='avg', selector='.summary-avg-data',
                                func='sel_text'),
                    Attr(name='total_motorcycles', selector='.summary-total',
                                func='sel_text', kws={'numbers': True}),
                    Attr(name='total_fuelups', selector='.summary-fuelups',
                                func='sel_text', kws={'numbers': True}),
                    Attr(name='total_miles', selector='.summary-miles',
                                func='sel_text', kws={'numbers': True}),
                ]
            ),
        ])
    ])
disp = Dispatcher()
disp.add_scraper(fuelly)
disp.run()

