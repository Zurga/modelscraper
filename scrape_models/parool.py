from modelscraper.dispatcher import Dispatcher
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from modelscraper.workers import WebSource
from modelscraper.parsers import HTMLParser
from pymongo import MongoClient

cl = MongoClient()

cookie = {'nl_cookiewall_version': '1'}

telegraaf_url = 'http://www.telegraaf.nl/jsp/search_result_page.jsp?method=&keyword=de&pagenr={}'
telegraaf_search = (Source(url=telegraaf_url.format(i)) for i in
                    range(1, 5001))

calendar = Template(
    name='archive_url', selector='', attrs=(
        Attr(name='url', selector='td a', func='sel_url',
             source=Source(active=False)),  # source is for next run
        )
    )

year = Template(
    name='archive_url_year', selector='.year-list__item',
    attrs=(
        Attr(name='url', selector='a', func='sel_url',
             source=True),  # source is for next run
        )
    )

article_url = Template(
    name='article_url', selector='ol.listing li',
    attrs=(
        Attr(name='url', selector='a', func='sel_url',
             source=Source(active=False)),  # source is for next run
    )
)

pagination = Template(
    name='next_page', selector='.pagination',
    attrs=(
        Attr(name='url', selector='a', func='sel_url'),
    )
)

telegraaf_search_result = Template(
    name='search_result', selector='li',
    db='telegraaf', table='article_urls',
    attrs=(
        Attr(name='url', selector='h2 a', func='sel_url',
             source=Source(active=False)),
    )
)

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

parool = ScrapeModel(
    name='parool', domain='http://www.parool.nl/',
    cookies=cookie,
    num_getters=1, phases=[
        Phase(source_worker=WebSource, parser=HTMLParser, sources=[
            Source(url="http://www.parool.nl/archief/2012")],
            templates=(calendar, year)
            ),
        Phase(source_worker=WebSource, parser=HTMLParser,
            templates=(
                article_url(db_type='MongoDB', db='parool',
                            table='article_urls'),
                pagination)
            ),
        Phase(source_worker=WebSource, parser=HTMLParser,
            templates=(article(db_type='MongoDB', db='parool',
                               table='articles'),
                       )
            ),
    ])

volkskrant = ScrapeModel(
    name='volkskrant', domain='http://www.volkskrant.nl/',
    cookies={'nl_cookiewall_version': '1'},
    num_getters=1, phases=[
        Phase(source_worker=WebSource, n_workers=2, parser=HTMLParser, sources=[
            Source(url="http://www.volkskrant.nl/archief/1997")],
            templates=(calendar, year)
            ),
        Phase(source_worker=WebSource, n_workers=2, parser=HTMLParser,
            templates=(article_url(db_type='MongoDB', db='volkskrant',
                                   table='article_urls'), pagination),
            ),
        Phase(source_worker=WebSource, n_workers=3, parser=HTMLParser,
            templates=(
                article(
                    selector='.article__main',
                    db_type='MongoDB', db='volkskrant', table='articles',
                    attrs=(
                        title_attr,
                        text_attr,
                        date_attr,
                        author_attr,
                        tags_attr(
                            selector='.category-bar__item a:nth-of-type(2)')
                    )
                ),
                )
            ),
    ])

telegraaf = ScrapeModel(
    name='telegraaf', domain='http://www.telegraaf.nl/',
    cookies={
             'adBlockerDisabledAfterNotification': 'false',
             'adBlockerNotificationShowed': 'true',
             },
    num_getters=1, phases=[
        Phase(n_workers=1,
            sources=(Source(url='http://www.telegraaf.nl'),)
            ),
        Phase(n_workers=2,
            sources=telegraaf_search,
            templates=(telegraaf_search_result,)
            ),
        Phase(n_workers=1,
            sources=telegraaf_search,
            templates=(
                article(
                    selector='.tg-article-page',
                    db_type='MongoDB', db='telegraaf', table='articles',
                    required=True,
                    preview=True,
                    attrs=(
                        title_attr,
                        text_attr,
                        date_attr(selector='.ui-gray3 span:nth-of-type(1)'),
                        author_attr(selector='.ui-gray3 span:nth-of-type(2)'),
                        tags_attr(
                            selector='.breadcrumbs a:last-of-type')
                    )
                ),
                )
            ),
    ])
