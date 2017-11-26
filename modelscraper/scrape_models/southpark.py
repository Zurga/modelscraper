from dispatcher import Dispatcher
from components import ScrapeModel, Phase, Template, Attr, Source
from pymongo import MongoClient
from workers import WebSource
from parsers import HTMLParser


cl = MongoClient()
db = cl.southpark
col = db.video

southpark = ScrapeModel(name='southpark', domain='http://southpark.cc.com/',
    num_getters=2, phases=[
    
    Phase(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url="http://southpark.cc.com/")],
        templates=(
            Template(
                name='video', selector='',
                db_type='mongo_db', db='southpark', table='video',
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
        Source(url="http://southpark.cc.com/")],
        templates=(
            Template(
                name='video', selector='',
                db_type='mongo_db', db='southpark', table='video',
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
disp.add_scraper(southpark)
disp.run()
