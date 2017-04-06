from dispatcher import Dispatcher
import models
from workers import WebSource
from parsers import HTMLParser
import string
from pymongo import MongoClient
import operator as op


uefa = models.ScrapeModel(
    name='eufa', domain='https://chaturbate.com/', num_getters=2, runs=[
    models.Run(source_worker=WebSource, parser=HTMLParser, sources=(
        models.Source(url="https://chaturbate.com/female-cams/"),),
        templates=[
            models.Template(
                name='model', selector='.content .list li',
                attrs=[
                    models.Attr(name='url', selector='a:nth-of-type(2)',
                                func='sel_attr', kws={'attr': 'href'},
                                source={'active': False,
                                        'src_template': 'https://chaturbate.com/api/panel/{}/'}),
                ]
            )]
    ),
    models.Run(source_worker=WebSource, parser=HTMLParser,
        templates=[
            models.Template(
                name='player', selector='.squad--team-player',
                db_type='mongo_db', db='uefa', table='players',
                attrs=[
                    models.Attr(name='name', selector='.squad--player-name',
                                func='sel_text'),
                    models.Attr(name='player_url', selector='.squad--player-name a',
                                func='sel_attr', kws={'attr': 'href'}),
                    models.Attr(name='img', selector='.squad--player-img img',
                                func='sel_attr', kws={'attr': 'src'}),
                ]
            ),
            # models.Template(
            #     name='team', selector='',
            #     db_type='mongo_db', func='update', db='uefa', table='players',
            #     attrs=[
            #         models.Attr(name='team', selector='h1.team-name', func='sel_text'),
            #     ]
            # )
        ]
    )]
)

disp = Dispatcher()
disp.add_scraper(uefa)
disp.run()

