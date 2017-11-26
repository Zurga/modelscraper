from modelscraper.dispatcher import Dispatcher
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from pymongo import MongoClient
from modelscraper.workers import WebSource
from modelscraper.parsers import HTMLParser


cl = MongoClient()
db = cl.lucky_tv
col = db.episode

sources = (Source(url="http://www.luckytv.nl/afleveringen/page/{}/".format(i))
           for i in range(1, 50))

LuckyTV = ScrapeModel(name='Lucky TV', domain='http://www.luckytv.nl/',
    num_getters=2, phases=[
    Phase(source_worker=WebSource, parser=HTMLParser, sources=sources,
        templates=(
            Template(
                name='episode', selector='article.video',
                db_type='mongo_db', db='lucky_tv', table='episodes',
                attrs=(
                    Attr(name='url', selector='a:nth-of-type(1)',
                         func='sel_url'),
                    Attr(name='title', selector='.video__title',
                         func='sel_text'),
                    Attr(name='date', selector='.video__date', func='sel_text'),
                )
            ),
        )
    ),
])

disp = Dispatcher()
disp.add_scraper(LuckyTV)
disp.run()
