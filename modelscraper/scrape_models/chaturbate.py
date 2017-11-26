from dispatcher import Dispatcher
import models
from workers import WebSource
from parsers import HTMLParser
import string
from pymongo import MongoClient
import operator as op


uefa = ScrapeModel(
    name='eufa', domain='https://chaturbate.com/', num_getters=2, phases=[
    Phase(source_worker=WebSource, parser=HTMLParser, sources=(
        Source(url="https://chaturbate.com/female-cams/"),),
        templates=[
            Template(
                name='model', selector='.content .list li',
                attrs=[
                    Attr(name='url', selector='a:nth-of-type(2)',
                                func='sel_attr', kws={'attr': 'href'},
                                source={'active': False,
                                        'src_template': 'https://chaturbate.com/api/panel/{}/'}),
                ]
            )]
    ),
    Phase(source_worker=WebSource, parser=HTMLParser,
        templates=[
            Template(
                name='player', selector='.squad--team-player',
                db_type='mongo_db', db='uefa', table='players',
                attrs=[
                    Attr(name='name', selector='.squad--player-name',
                                func='sel_text'),
                    Attr(name='player_url', selector='.squad--player-name a',
                                func='sel_attr', kws={'attr': 'href'}),
                    Attr(name='img', selector='.squad--player-img img',
                                func='sel_attr', kws={'attr': 'src'}),
                ]
            ),
            # Template(
            #     name='team', selector='',
            #     db_type='mongo_db', func='update', db='uefa', table='players',
            #     attrs=[
            #         Attr(name='team', selector='h1.team-name', func='sel_text'),
            #     ]
            # )
        ]
    )]
)

disp = Dispatcher()
disp.add_scraper(uefa)
disp.run()

