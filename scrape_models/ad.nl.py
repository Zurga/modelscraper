from modelscraper.dispatcher import Dispatcher
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from pymongo import MongoClient


search_url = 'https://mobileapi.ad.nl/mobile/lists/search'
sources = (Source(url=search_url, params={'query': w}) for w in words)

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

next_page = Template(
    name='next_page',
    selector='paging',
    attrs=(
        Attr(name='paging',

ad = ScrapeModel(
    name='ad.nl', domain='mobileapi.ad.nl', phases=[
        Phase(n_workers=2, sources=sources, templates=(

