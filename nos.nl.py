from modelscraper.dispatcher import Dispatcher
from modelscraper.models import ScrapeModel, Run, Template, Attr, Source
from modelscraper.workers import WebSource
from modelscraper.parsers import HTMLParser
import datetime


categories = [
    'binnenland',
    'buitenland',
    'politiek',
#    'economie',
#    'tech',
#    'opmerkelijk',
#    'cultuur-en-media',
#    'koningshuis',
]
now = datetime.datetime.now()
begin = datetime.datetime.strptime('2010-01-01', '%Y-%m-%d')
timezone = datetime.timezone(datetime.timedelta(0, 3600))

dates = [begin + datetime.timedelta(days=d) for d in range(0, (now -
                                                               begin).days)]

nos_sources = (Source(url="http://nos.nl/nieuws/{}/archief/{}".format(
    cat, date.strftime('%Y-%m-%d')),
    attrs=(Attr(name='category', value=cat),),
    copy_attrs=True) for cat in categories for date in dates)

title_attr = Attr(name='title', selector='h1', func='sel_text')
text_attr = Attr(name='text', selector='.article_body', func='sel_text')
date_attr = Attr(name='date', selector='time:nth-of-type(1)', func='sel_attr',
                 kws={'attr': 'datetime'})
author_attr = Attr(name='author', selector='span[itemprop="author"]',
                   func='sel_text')
tags_attr = Attr(name='tags', selector='.ib.space-right a.link-grey',
                 func='sel_text')

article = Template(
    name='article',
    attrs=(
        title_attr,
        text_attr,
        date_attr,
        author_attr,
        tags_attr
    )
)
nos = ScrapeModel(name='nos.nl', domain='http://nos.nl', num_getters=2, runs=[
    Run(source_worker=WebSource, parser=HTMLParser, sources=nos_sources,
        templates=[
            Template(
                name='article_url', selector='#archief li',
                db_type='mongo_db', db='nos_nl', table='article_urls',
                attrs=[
                    Attr(name='url', selector='a', func='sel_attr',
                         kws={'attr': 'href'}, source={'active': False}),
                ]
            )
        ]
    ),
    Run(templates=(article(
        db_type='mongo_db',
        db='nos_nl',
        table='articles'),
    )
    )
]
)

disp = Dispatcher()
disp.add_scraper(nos)
disp.run()
