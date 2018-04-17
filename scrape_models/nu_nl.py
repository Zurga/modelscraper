from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source


base_url = "http://www.nu.nl/block/html/articlelist?footer=ajax&section={section}&limit=20&offset={offset}&show_tabs=0"
sections = ['buitenland', 'binnenland', 'economie', 'algemeen', 'tech', 'sport']
sources = (
    Source(url=base_url.format(section=section, offset=offset),
           copy_attrs=['category'], attrs=[
               Attr(name='category', value=[section])])
    for section in sections for offset in range(0, 200000, 20))

headline= Template(
    name='headline',
    selector='li',
    db='nu_nl',
    db_type='MongoDB',
    table='article_urls',
    attrs=[
        Attr(name='url', selector='a', func='sel_url',
             source={'active': False, 'copy_attrs': 'category'}),
        Attr(name='title', selector='.title', func='sel_text'),
        Attr(name='excerpt', selector='.excerpt', func='sel_text')
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
    db_type='MongoDB',
    table='articles',
    attrs=(
        title_attr,
        text_attr,
        date_attr,
        author_attr,
        tags_attr
    )
)

nu = ScrapeModel(name='nu.nl', domain='http://nu.nl', phases=[
    Phase(n_workers=2, sources=sources, templates=(headline,)),
    Phase(n_workers=2, templates=(article,))
])
