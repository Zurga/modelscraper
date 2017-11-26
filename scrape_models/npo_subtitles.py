from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from modelscraper.parsers import TextParser
from modelscraper.dispatcher import Dispatcher
from pymongo import MongoClient


cl = MongoClient()
sources = (Source(url=a['url'][0]) for a in cl.dwdd.episode_urls.find())

programs_az = Phase(
    sources=[
        Source(url="http://www.npo.nl/programmas/a-z", params={'page': i})
        for i in range(0, 1)],
        templates=(
            Template(
                name='program', selector='.content-column.quarter',
                db_type='mongo_db', db='npo_tv_programs', table='programs',
                attrs=(
                    Attr(name='title', selector='h3', func='sel_text'),
                    Attr(name='url', selector='a.full-link', func='sel_url',
                        source=Source(active=False)), # source is for next run
                )
            ),
        )
    )

nos_search = 'https://www.npo.nl/de-wereld-draait-door/VARA_101377717/search?media_type=broadcast&start_date=&end_date=&start={}&rows=100'
episodes_phase = Phase(n_workers=5, sources=(Source(url=nos_search.format(start))
                 for start in range(0, 2194, 100)),
            templates=(
            Template(
                name='episodes', selector='.list-item',
                db_type='mongo_db', db='dwdd', table='episode_urls',
                attrs=(
                    Attr(name='url', selector='.span4 a', func='sel_url',
                        source=Source(active=False)),
                )),
            )
        ),

npo_tv_programs = ScrapeModel(name='npo_tv_programs', domain='http://npo.nl',
    num_getters=2, phases=[
    Phase(n_workers=10, sources=sources, templates=(
        Template(name='episode', selector='.column-player-info', db='dwdd', func='update',
                 table='episodes', db_type='mongo_db', attrs=(
                    Attr(name='date', selector='ul.the-player-meta-block__date-tags',
                         func='sel_text'),
                    Attr(name='description', selector='.overflow-description',
                         func='sel_text'),
                )
            ),
        )
    ),
])

disp = Dispatcher()
disp.add_scraper(npo_tv_programs)
disp.run()
