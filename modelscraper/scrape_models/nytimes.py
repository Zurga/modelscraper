from dispatcher import Dispatcher
from models import ScrapeModel, Run, Template, Attr, Source
from pymongo import MongoClient
from workers import WebSource
from parsers import HTMLParser


cl = MongoClient()
db = cl.nytimes
col = db.menu

nytimes = ScrapeModel(name='nytimes', domain='https://www.nytimes.com/',
    num_getters=2, runs=[

    Run(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url="https://www.nytimes.com/")],
        templates=(
            Template(
                name='menu', selector='#site-index-navigation li',
                db_type='mongo_db', db='nytimes', table='menu',
                attrs=(
                    Attr(name='url', selector='a', func='sel_url',
                        source=Source(active=False)), # source is for next run
                )
            ),
        )
    ),

    Run(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url="https://www.nytimes.com/")],
        templates=(
            Template(
                name='articlelist', selector='',
                db_type='mongo_db', db='nytimes', table='articles',
                attrs=(
                    Attr(name='title', selector='h1', func='sel_text'),

                    Attr(name='text', selector='.story-body-supplemental p',
                         func='sel_text'),
                    Attr(name='writer', selector='span.byline-author',
                         func='sel_text'),
                    Attr(name='text', selector='.story-body-supplemental',
                         func='sel_tex')
                    Attr(name='date', selector='time.datine', func='sel_attr',
                         kws={'attr': 'datetime'}),
                    Attr(name='related', func='sel_url',
                         selector='#related-combined-coverage a.story-link'),
                    Attr(name='text',
                         selector='.story-body-supplemental p', func='sel_text'),
                )
            ),
            Template(
                name='submenu', selector='#main .subnavigation li',
                db_type='mongo_db', db='nytimes', table='submenu',
                attrs=(
                    Attr(name='url', selector='a', func='sel_url',
                        source=True), # source is for next run
                )
            ),
        )
    ),

])

disp = Dispatcher()
disp.add_scraper(nytimes)
disp.run()
