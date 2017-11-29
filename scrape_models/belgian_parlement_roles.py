from dispatcher import Dispatcher
from components import ScrapeModel, Phase, Template, Attr, Source
from pymongo import MongoClient
from workers import WebSource
from parsers import HTMLParser


cl = MongoClient()
db = cl.belgian_parlement_roles
col = db.government

belgian_parlement_roles = ScrapeModel(name='belgian_parlement_roles', domain='https://fr.wikipedia.org/',
    num_getters=2, phases=[

    Phase(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url="https://fr.wikipedia.org/wiki/Liste_des_gouvernements_de_la_Belgique")],
        templates=(
            Template(
                name='government', selector='.wikitable tr td:nth-of-type(2)',
                attrs=(
                    Attr(name='url', selector='a', func='sel_url',
                        source=Source(active=False)), # source is for next run
                )
            ),
        )
    ),

    Phase(source_worker=WebSource, parser=HTMLParser,
        templates=(
            Template(
                name='government', selector='table:nth-of-type(1) tr',
                db_type='mongo_db', db='belgian_politics', table='politicians',
                attrs=(
                    Attr(name='url', selector='td:nth-of-type(2) a', func='sel_url'),
                    Attr(name='title', selector='td:nth-of-type(1)', func='sel_text'),
                )
            ),
        )
    ),

])

disp = Dispatcher()
disp.add_scraper(belgian_parlement_roles)
disp.run()
