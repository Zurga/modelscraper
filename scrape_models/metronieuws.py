from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from pymongo import MongoClient


cl = MongoClient()
categories = {39: 'binnenland',
              2: 'buitenland',
              }
category_url = "http://www.metronieuws.nl/getsectionlist/{}/{}/0"

binnenland = (Source(url=category_url.format(39, i), json_key=['data'],
                  attrs=[Attr(name='category', value='binnenland')])
            for i in range(1, 2400))

buitenland = (Source(url=category_url.format(2, i), json_key=['data'],
                  attrs=[Attr(name='category', value='buitenland')])
            for i in range(1, 1900))

sources = [*binnenland, *buitenland]

title_attr = Attr(name='title', selector='h1', func='sel_text')
text_attr = Attr(name='text', selector='.article_body', func='sel_text')
date_attr = Attr(name='date', selector='time:nth-of-type(1)', func='sel_attr',
                 kws={'attr': 'datetime'})
author_attr = Attr(name='author', selector='span[itemprop="author"]',
                   func='sel_text')
tags_attr = Attr(name='tags', selector='.tag',
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
headline_phase = Phase(
    sources=sources, n_workers=5, templates=[
        Template(
            name='headline', selector='.row', db='metronieuws',
            db_type='MongoDB', kws={'key':'url'},
            table='article_urls', attrs=[
                Attr(name='url', selector='a.shadow-block',
                        func='sel_attr', kws={'attr': 'href'},
                        source=Source(active=False, copy_attrs='category')),
                Attr(name='title', selector='h3', func='sel_text'),
                Attr(name='excerpt', selector='div > p', func='sel_text'),
                Attr(name='date', selector='div.wrapper.small div:nth-of-type(1)',
                            func='sel_text'),
                Attr(name='num_reactions', selector='div.amount', func='sel_text'),
            ]
        )
    ])

metro = ScrapeModel(
    name='metronieuws.nl', domain='http://metronieuws.nl', num_getters=5,
    phases=[
        headline_phase,
        Phase(sources=sources, n_workers=3, templates=[
            article(
                selector='.artikel', db='metronieuws',
                table='articles', db_type='MongoDB', attrs=[
                    title_attr,
                    text_attr(selector='.content .field-items .field-item > p'),
                    author_attr(selector='.username'),
                    Attr(name='date', func='sel_attr', kws={'attr':'content'},
                         selector='.small span[datatype="xsd:dateTime"]'),
                    tags_attr,
                ])
        ])
    ])

