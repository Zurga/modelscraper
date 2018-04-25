from dispatcher import Dispatcher
from components import ScrapeModel, Phase, Template, Attr, Source
from workers import WebSource
from parsers import HTMLParser
import string
from pymongo import MongoClient


petitions = ScrapeModel(
    name='petitions', domain='https://petities.nl/', num_getters=2,
    phases=[
        Phase(source_worker=WebSource, parser=HTMLParser, sources=(
            Source(url="https://petities.nl/petitions/borstkankeronderzoek-vervroegen/signatures?locale=nl"),),
            templates=[
                Template(name='next_page', selector='.navigation-bar .navigation-bar',
                         attrs=[Attr(name='url', selector='a', func='sel_url', kws={'attr': 'href'},
                                     source=True)]),
                Template(name='signature', selector='.petition-signature-list',
                         db_type='MongoDB', db='petitions', table='borstkanker',
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
