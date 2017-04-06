from dispatcher import Dispatcher
import models
from workers import WebSource
from parsers import HTMLParser
import string
from pymongo import MongoClient
import operator as op


fuelly = models.ScrapeModel(
    name='fuelly', domain='http://www.fuelly.com', num_getters=1, runs=[
    models.Run(source_worker=WebSource, parser=HTMLParser, sources=(
        models.Source(url="http://www.fuelly.com/motorcycle"),),
        templates=[
            models.Template(
                name='motorcycle_link', selector='.models-list li',
                attrs=[
                    models.Attr(name='amount',func='sel_text', kws={'regex': '\((\d+)\)',
                                                                    'debug': True,
                                                                    }),
                    models.Attr(name='url', selector='a',
                                func='sel_url', source={'active': False},
                                source_condition={'amount': '> 2'}),
                ]
            )]
    ),
    models.Run(source_worker=WebSource, parser=HTMLParser,
        templates=[
            models.Template(
                name='motorcycle', selector='.model-year-item',
                db_type='mongo_db', db='fuelly', table='motorcycles',
                attrs=[
                    models.Attr(name='name', selector='.summary-view-all-link a',
                                func='sel_text'),
                    models.Attr(name='url', selector='.summary-view-all-link a',
                                func='sel_url'),
                    models.Attr(name='year', selector='.summary-year',
                                func='sel_text', kws={'numbers': True}),
                    models.Attr(name='avg', selector='.summary-avg-data',
                                func='sel_text'),
                    models.Attr(name='total_motorcycles', selector='.summary-total',
                                func='sel_text', kws={'numbers': True}),
                    models.Attr(name='total_fuelups', selector='.summary-fuelups',
                                func='sel_text', kws={'numbers': True}),
                    models.Attr(name='total_miles', selector='.summary-miles',
                                func='sel_text', kws={'numbers': True}),
                ]
            ),
        ])
    ])
disp = Dispatcher()
disp.add_scraper(fuelly)
disp.run()

