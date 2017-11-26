from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from modelscraper.parsers import TextParser
from modelscraper.dispatcher import Dispatcher
from pymongo import MongoClient


cl = MongoClient()
urls = (Source(url='https://tt888.omroep.nl/tt888/' + a['url'][0].split('/')[-1],
               attrs=(Attr(name='url', value=a['url']),))
        for a in cl.dwdd.episodes.find())

subtitles = ScrapeModel(
    name='subtitles', domain='https://tt888.omroep.nl/',
    phases=[
        Phase(n_workers=5, sources=urls, parser=TextParser,
            templates=(
                Template(
                    name='subtitle', db_type='mongo_db', db='dwdd',
                    table='episodes', func='update', kws={'key': 'url'},
                    attrs=(
                        Attr(name='subtitles', func='sel_text'),
                        )
                ),
            )
            )
    ])
del cl
d = Dispatcher()
d.add_scraper(subtitles)
d.run()
