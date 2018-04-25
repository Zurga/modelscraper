from modelscraper.dispatcher import Dispatcher
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from pymongo import MongoClient
from modelscraper.sources import WebSource
from modelscraper.parsers import HTMLParser


series_url = "https://www.npo.nl/media/series?page={}&dateFrom=2014-01-01&tilemapping=normal&tiletype=teaser&pageType=catalogue"
npo_tv_programs = ScrapeModel(name='npo_tv_programs', domain='http://npo.nl',
    num_getters=2, phases=[
    Phase(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url=series_url.format(i)) for i in range(0, 242)],
        templates=(
            Template(
                name='program', selector='.content-column.quarter',
                db_type='MongoDB', db='npo_tv_programs', table='programs',
                attrs=(
                    Attr(name='title', selector='h3', func='sel_text'),
                    Attr(name='url', selector='a.full-link', func='sel_url',
                        source=Source(active=False)), # source is for next run
                )
            ),
            Template(
                name='next_url'),
        )
    ),
    Phase(source_worker=WebSource, parser=HTMLParser,
        templates=(
            Template(
                name='episodes', selector='.item-list.item-container div.item',
                db_type='MongoDB', db='npo_tv_programs', table='episodes',
                attrs=(
                    Attr(name='episode_url', selector='a', func='sel_url',
                        source=Source(active=False)), # source is for next run

                    Attr(name='episode_title', selector='h3', func='sel_text'),

                    Attr(name='episode_text', selector='p', func='sel_text'),
                    Attr(name='program', selector='meta[property="og:title"]',
                         func='sel_text'),
                    Attr(name='date', selector='h4', func='sel_text',
                         kws={'all_text': False})
                )
            ),
            Template(name='more_episodes', selector='', attrs=[
                Attr(name='num_result', selector='div.search-results',
                     func='sel_attr', kws={'attr': 'data-num-found'}),

                Attr(name='pagesize', selector='div.search-results',
                     func='sel_attr', kws={'attr': 'data-rows'}),

                Attr(name='start', selector='div.search-results',
                     func='sel_attr', kws={'attr': 'data-start'}),

                Attr(name='result_form', selector='#program-search-form',
                     func='fill_form')
                ]),
        )
    ),
])

disp = Dispatcher()
disp.add_scraper(npo_tv_programs)
disp.run()
