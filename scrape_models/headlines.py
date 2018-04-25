from dispatcher import Dispatcher
from components import ScrapeModel, Phase, Template, Attr, Source
from pymongo import MongoClient
from workers import WebSource
from parsers import HTMLParser


cl = MongoClient()
db = cl.headlines
col = db.category

headlines = ScrapeModel(name='headlines', domain='http://www.headlines24.nl/',
    num_getters=2, phases=[
    
    Phase(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url="http://www.headlines24.nl/")],
        templates=(
            Template(
                name='category', selector='',
                db_type='MongoDB', db='headlines', table='category',
                attrs=(
                    Attr(name='url', selector='a', func='sel_url',
                        source=Source(active=False)), # source is for next run

                    Attr(name='title', selector='h1', func='sel_text'),

                    Attr(name='text', selector='p', func='sel_text'),
                )
            ),
        )
    ),
    
    Phase(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url="http://www.headlines24.nl/")],
        templates=(
            Template(
                name='category', selector='',
                db_type='MongoDB', db='headlines', table='category',
                attrs=(
                    Attr(name='url', selector='a', func='sel_url',
                        source=Source(active=False)), # source is for next run

                    Attr(name='title', selector='h1', func='sel_text'),

                    Attr(name='text', selector='p', func='sel_text'),
                )
            ),
        )
    ),
    
])

disp = Dispatcher()
disp.add_scraper(headlines)
disp.run()
