from modelscraper.dispatcher import Dispatcher
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source


search_url = 'https://www.rtlnieuws.nl/search/nieuws/{}'
search_terms = ['economie', 'nederland']
title_attr = Attr(name='title', selector='h1', func='sel_text')
text_attr = Attr(name='text', selector='p', func='sel_text')
date_attr = Attr(name='date', selector='time', func='sel_text')
author_attr = Attr(name='author', selector='span[itemprop="author"]',
                   func='sel_text')
tags_attr = Attr(name='tags', selector='.tag-list a.cta',
                 func='sel_text')

article = Template(
    name='article', selector='.col__inner',
    attrs=(
        title_attr,
        text_attr,
        date_attr,
        author_attr,
        tags_attr
    )
)

rtl= ScrapeModel(
    name='rtl', domain='http://www.rtlnieuws.nl/',
    num_getters=1, phases=[
        Phase(sources=[
            Source(url="http://www.parool.nl/archief/2012")],
            templates=(calendar, year)
            ),
        Phase(templates=(
                article_url(db_type='mongo_db', db='parool',
                            table='article_urls'),
                pagination)
            ),
        Phase(templates=(article(db_type='mongo_db', db='parool',
                               table='articles'),
                       )
            ),
    ])
