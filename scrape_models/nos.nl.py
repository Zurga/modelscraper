from dispatcher import Dispatcher
from components import as models
from pymongo import MongoClient
from workers import WebSource
from parsers.html_parser import HTMLParser
import datetime


print(dir()
cl = MongoClient()
db = cl.nos_nl
col = db.headlines
headlines = col.find()

categories = [
    'binnenland',
    'buitenland',
    'politiek',
    'economie',
    'tech',
    'opmerkelijk',
    'cultuur-en-media',
    'koningshuis',
]

now = datetime.datetime.now()
begin = datetime.datetime.strptime('2010-01-01', '%Y-%m-%d')
timezone = datetime.timezone(datetime.timedelta(0, 3600))

last = max(h['datetime'] for h in headlines if h['datetime'])

if last:
    begin = datetime.datetime.strptime(last, '%Y-%m-%dT%H:%M:%S%z')
    now = datetime.datetime.now(tz=begin.tzinfo)
dates = [begin + datetime.timedelta(days=d) for d in range(0, (now - begin).days)]
nos = ScrapeModel(name='nos.nl', domain='http://nos.nl', num_getters=2, phases=[
    Phase(source_worker=WebSource, parser=HTMLParser, sources=(
        Source(url="http://nos.nl/nieuws/%s/archief/%s" %(cat, date.strftime('%Y-%m-%d')),
                      attrs=[Attr(name='category', value=cat),
                             ])
                    for cat in categories for date in dates),
        templates=[
            Template(
                name='headline', selector='#archief li',
                db_type='MongoDB', db='nos_nl', table='headlines',
                attrs=[
                    Attr(name='url', selector='a', func='sel_attr',
                                kws={'attr': 'href'}, source={'active': False}),
                    Attr(name='title', selector='.link-hover', func='sel_text'),
                    Attr(name='datetime', selector='time', func='sel_attr',
                                kws={'attr': 'datetime'}),
                ]
            )
        ]
    ),
    Phase(source_worker=WebSource, parser=HTMLParser,
        templates=[
            Template(name='headline', db_type='MongoDB', db='nos_nl',
                            table='articles',
                attrs=[
                    Attr(name='title', selector='h1', func='sel_text'),
                    Attr(name='text', selector='.article_body', func='sel_text'),
                    Attr(name='publish', selector='time:nth-of-type(1)', func='sel_attr',
                                kws={'attr': 'datetime'}),
                    Attr(name='edit', selector='time:nth-of-type(2)', func='sel_attr',
                                kws={'attr': 'datetime'}),
                ]
            )
        ]
    )
]
)

disp = Dispatcher()
disp.add_scraper(nos)
disp.run()
