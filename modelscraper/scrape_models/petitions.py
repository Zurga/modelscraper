from dispatcher import Dispatcher
from models import ScrapeModel, Run, Template, Attr, Source
from workers import WebSource
from parsers import HTMLParser
import string
from pymongo import MongoClient


petitions = ScrapeModel(
    name='petitions', domain='https://petities.nl/', num_getters=2,
    runs=[
        Run(source_worker=WebSource, parser=HTMLParser, sources=(
            Source(url="https://petities.nl/petitions/borstkankeronderzoek-vervroegen/signatures?locale=nl"),),
            templates=[
                Template(name='next_page', selector='.navigation-bar .navigation-bar',
                         attrs=[Attr(name='url', selector='a', func='sel_url', kws={'attr': 'href'},
                                     source=True)]),
                Template(name='signature', selector='.petition-signature-list',
                         db_type='mongo_db', db='petitions', table='borstkanker',
                         attrs=[
                             Attr(name='name', selector='.petition-signature-name',
                                  func='sel_text'),
                             Attr(name='time', selector='.signature-time', func='sel_text'),
                             Attr(name='location', selector='.petition-signature-location',
                                  func='sel_text'),
                             Attr(name='occupation', selector='.petition-signature-occupation',
                                  func='sel_text')
                        ])
            ]
        )
    ]
)

ds = Dispatcher()
ds.add_scraper(petitions)
ds.run()
