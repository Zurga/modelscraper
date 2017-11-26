from dispatcher import Dispatcher
from components import ScrapeModel, Phase, Template, Attr, Source
from pymongo import MongoClient
from workers import WebSource
from parsers import HTMLParser


cl = MongoClient()
db = cl.erowid
col = db.drug_report

erowid = ScrapeModel(name='erowid', domain='https://www.erowid.org/experiences/',
    num_getters=2, phases=[
    Phase(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url="https://www.erowid.org/experiences/exp.cgi?ShowViews=1&Cellar=0&Start=0&Max=24777")],
        templates=(
            Template(
                name='report_url', selector='.exp-list-table tr',
                source={'active': False, 'copy_attrs': True},
                attrs=(
                    Attr(name='url', selector='td:nth-of-type(2) a',
                         func='sel_url'),

                    Attr(name='title', selector='td:nth-of-type(2) a',
                         func='sel_text'),

                    Attr(name='rating', selector='td:nth-of-type(1) img',
                         func='sel_attr', kws={'attr': 'alt'}),

                    Attr(name='author', selector='td:nth-of-type(3)',
                         func='sel_text'),

                    Attr(name='substances', selector='td:nth-of-type(4)',
                         func='sel_text',
                         kws={'replacers': '&', 'substitute': ',', 'regex':
                              '([A-z0-9\-]+\s*[A-z0-9\-*\s]*)'}),

                    Attr(name='date', selector='td:nth-of-type(5)', func='sel_text'),

                    Attr(name='views', selector='td:nth-of-type(6)',
                         func='sel_text'),
                )
            ),
        )
    ),

    Phase(source_worker=WebSource, parser=HTMLParser,
        templates=(
            Template(
                name='drug_report', selector='',
                db_type='mongo_db', db='erowid', table='drug_report',
                attrs=(
                    Attr(name='text', selector='.report-text-surround', func='sel_text'),
                    Attr(name='weight', selector='td.bodyweight-amount', func='sel_text'),
                )
            ),
        )
    ),
])

disp = Dispatcher()
disp.add_scraper(erowid)
disp.run()
