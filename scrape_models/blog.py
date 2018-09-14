from modelscraper.components import ScrapeModel, Template, Attr
from modelscraper.sources import WebSource

text = Attr(name='text', func='sel_html')
title = Attr(name='title', func='sel_text')
pictures = Attr(name='pictures', func='sel_attr', selector='img',
                kws={'attr': 'src'})
date = Attr(name='date', func='sel_text')
related = Attr(name='related', func='sel_url')
author = Attr(name='author', func='sel_text')
tags = Attr(name='author', func='sel_text')

article = Template(
    name='article',
    attrs=(
        text,
        title,
        date,
        author,
        tags,
        pictures,
        related
    ),
    db='news', db_type='MongoDB'
)

article_url = Attr(name='url', func='sel_url')

tweakers_article_source = WebSource()
tweakers_list = Template(
    selector='',
    attrs=[article_url(selector='', emits=tweakers_article_source)]
)

tweakers = article(
    source=tweakers_article_source,
    table='tweakers.net',
    selector='#contentArea',
    attrs=(
        text(selector='.article p'),
        title(selector='h1'),
        date(selector='span.articleMeta'),
        author(selector='span[itemprop="author"]'),
        tags(selector='.relatedSubjectItems a'),
        pictures,
        related(selector='.relatedContentItems'),
    ))

tweakers_article_source = WebSource()
tweakers_list = Template(
    selector='',
    attrs=[article_url(selector='', emits=tweakers_article_source)]
)
security = article(
    source=WebSource(),
    table='security.nl',
    selector='.posting_body_container',
    attrs=(
        text(selector='.posting_content p'),
        title(selector='h1'),
        date(selector='.left', kws={'all_text': False}),
        author(selector='.left b a'),
        tags,
        pictures,
        related,
    ))

tweakers_article_source = WebSource()
tweakers_list = Template(
    selector='',
    attrs=[article_url(selector='', emits=tweakers_article_source)]
)
nos_nl = article(
    source=WebSource(),
    table='nos.nl',
    attrs=(
        text(selector='.article_body p'),
        title(selector='h1'),
        date(selector='time:nth-of-type(1)', func='sel_attr',
             kws={'attr': 'datetime'}),
        tags(selector='.link-grey'),
        pictures,
        related,
        author(selector='.bio__name'),
    ))

tweakers_article_source = WebSource()
tweakers_list = Template(
    selector='',
    attrs=[article_url(selector='', emits=tweakers_article_source)]
)
nu_nl = article(
    source=WebSource(),
    table='nu.nl',
    selector='.column-content-background',
    attrs=(
        text(selector='p'),
        title(selector='h1'),
        date(selector='.published span.small'),
        author(selector='span.author'),
        tags(selector='.article.tags a span'),
        pictures,
        related,
    ))
