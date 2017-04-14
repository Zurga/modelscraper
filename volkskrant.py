from modelscraper.models import ScrapeModel, Run, Template, Attr, Source
from modelscraper.parsers import JSONParser
from pymongo import MongoClient

cl = MongoClient()


title_attr = Attr(name='title', selector='title', func='sel_text')
text_attr = Attr(name='text', selector='body_elements', func='sel_dict')
date_attr = Attr(name='date', selector='publish_date', func='sel_text')
author_attr = Attr(name='author', selector='written_by', func='sel_text')
tags_attr = Attr(name='tags', selector=('tags', 'name'), func='sel_text')
category_attr = Attr(name='category', selector=('section', 'name'),
                     func='sel_text')
counters_attr = Attr(name='counters', selector='counters', func='sel_text')
intro_attr = Attr(name='excerpt', selector='intro', func='sel_text')
type_attr = Attr(name='excerpt', selector='type', func='sel_text')

article = Template(
    name='article',
    db='volkskrant', table='articles',
    db_type='mongo_db',
    attrs=(
        title_attr,
        text_attr,
        date_attr,
        author_attr,
        tags_attr,
        category_attr,
        counters_attr,
        intro_attr,
        type_attr
    )
)

article_url = 'http://vkplusmobilebackend.persgroep.net/rest/content/articles/{}'
search_url = 'http://vkplusmobilebackend.persgroep.net/rest/content/articles?query=&metadataNeeded=true&limit=10000'
next_page_url = 'http://vkplusmobilebackend.persgroep.net/rest/content/articles?query=&metadataNeeded=true&limit=10000&offset={}'

search_result = Template(
    name='search_result', db='volkskrant', table='article_urls',
    func='create',
    db_type='mongo_db', selector=('results', 'previews'),
    attrs=(
        Attr(name='id', selector=('content_link', 'id'), func='sel_text',
             source={'src_template': article_url, 'active': False}),
    ),
)

next_search = Template(
    name='next_result',
    attrs=(
        Attr(name='next_limit', selector=('results', 'next_offset'),
             func='sel_text', source={'src_template': next_page_url}),
    )
)

sources = (Source(url=search_url),)

volkskrant = ScrapeModel(
    name='volkskrant', domain='volkskrant',
    runs=[
        Run(parser=JSONParser, n_workers=1, sources=sources,
            templates=(search_result, next_search)),
        Run(parser=JSONParser, n_workers=5, sources=sources, templates=(article,)),
    ])
