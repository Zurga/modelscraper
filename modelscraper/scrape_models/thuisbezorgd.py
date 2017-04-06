from dispatcher import Dispatcher
from models import ScrapeModel, Run, Template, Attr, Source
from pymongo import MongoClient
from workers import WebSource
from parsers import HTMLParser


cl = MongoClient()
db = cl.thuisbezorgd
col = db.reviews

thuisbezorgd = ScrapeModel(name='thuisbezorgd', domain='http://thuisbezorgd.nl',
                                  num_getters=2, runs=[
    Run(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url="https://www.thuisbezorgd.nl/")],
        templates=(
            Template(
                name='sections', selector='',
                attrs=(
                    Attr(name='url', selector='a[href*="eten-bestellen-"]', func='sel_url',
                                source=Source()), # source is for next run
                )
            ),
            Template(
                name='restaurant', selector='.restaurant',
                db_type='mongo_db', db='thuisbezorgd', table='restaurants',
                attrs=(
                    Attr(name='url', selector='a.restaurantname', func='sel_url',
                                source=Source(active=False, src_template='{}')), # source is for next run

                    Attr(name='name', selector='a.restaurantname', func='sel_text'),

                )
            ),
        )
    ),
    Run(source_worker=WebSource, parser=HTMLParser,
        templates=(
            Template(
                name='reviews', selector='',
                db_type='mongo_db', db='thuisbezorgd', table='reviews',
                attrs=(
                    Attr(name='url', selector='a', func='sel_url',
                                source=Source(active=False)), # source is for next run

                    Attr(name='title', selector='h1', func='sel_text'),

                    Attr(name='text', selector='p', func='sel_text'),
                )
            ),
        )
    ),
    ]

)

disp = Dispatcher()
disp.add_scraper(thuisbezorgd)
disp.run()
