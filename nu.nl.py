from modelscraper.dispatcher import Dispatcher
from modelscraper.models import ScrapeModel, Run, Template, Attr, Source
from pymongo import MongoClient


client = MongoClient()
col = client.nu_nl
db = col.headlines

scraped = [h['url'] for h in col.articles.find()]
print(len(scraped))
sources = [Source(url=h['url'], attrs=[Attr(name='category', value='politiek')])
           for h in db.find({'category':'politiek'}) if h['url'] not in scraped]
print(len(sources))

# Source(url="http://www.nu.nl/block/html/articlelist?footer=ajax&section=economie&limit=20&offset={}&show_tabs=0".
#                 format(i)) for i in range(0, 2000000, 20)
url = "http://www.nu.nl/block/html/articlelist?footer=ajax&section=politiek&limit=20&offset={}&show_tabs=0"

headline= Template(
    name='headline',
    selector='li',
    db='nu_nl',
    db_type='mongo_db',
    table='headlines',
    required=True,
    attrs=[
        Attr(name='url', selector='a', func='sel_attr',
                    kws={'attr': 'href'}, source={'active': False}),
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

nu = ScrapeModel(name='nu.nl', domain='http://nu.nl', runs=[
    # Run(sources=sources, templates=(headline,)),
    Run(sources=sources, templates=(article,))
])

disp = Dispatcher()
disp.add_scraper(nu)
disp.run()
