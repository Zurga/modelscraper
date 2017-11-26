from modelscraper.dispatcher import Dispatcher
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from pymongo import MongoClient


client = MongoClient()
col = client.nu_nl
db = col.headlines

url = "http://www.nu.nl/block/html/articlelist?footer=ajax&section=buitenland&limit=20&offset={}&show_tabs=0"
sources = (Source(url=url.format(i), copy_attrs=True,
                  attrs=[Attr(name='category', value='buitenland')])
           for i in range(0, 200000, 20))

headline= Template(
    name='headline',
    selector='li',
    db='nu_nl',
    db_type='mongo_db',
    table='article_urls',
    kws={'key': 'url'},
    required=True,
    attrs=[
        Attr(name='url', selector='a', func='sel_attr',
                    kws={'attr': 'href'}, source={'active': False,
                                                  'copy_attrs': 'category'}),
        Attr(name='title', selector='.title', func='sel_text'),
        Attr(name='excerpt', selector='.excerpt', func='sel_text'),
    ]
    )

title_attr = Attr(name='title', selector='h1', func='sel_text')
text_attr = Attr(name='text', selector='p', func='sel_text')
date_attr = Attr(name='date', selector='.published span.small',
                        func='sel_text')
author_attr = Attr(name='author', selector='span.author',
                          func='sel_text')
tags_attr = Attr(name='tags', selector='.article.tags a span',
                        func='sel_text')

article = Template(
    name='article', selector='.column-content-background',
    db='nu_nl',
    db_type='mongo_db',
    table='articles',
    attrs=(
        title_attr,
        text_attr,
        date_attr,
        author_attr,
        tags_attr
    )
)
'''
parsed = [a['url'] for a in col.articles.find({'category': 'binnenland'})]
print('parsed', len(parsed))
sources = [Source(url=a['url'], attrs=[Attr(name='category',
                                            value='binnenland')])
           for a in db.find({'category': 'binnenland'})
           if a['url'] not in parsed]
'''
nu = ScrapeModel(name='nu.nl', domain='http://nu.nl', phases=[
    Phase(n_workers=5, sources=sources, templates=(headline,)),
    Phase(n_workers=5, templates=(article,))
])
