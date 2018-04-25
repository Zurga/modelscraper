from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source

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

tweakers = article(
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

security = article(
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

nos_nl = article(
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

nu_nl = article(
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


