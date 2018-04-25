from dispatcher import Dispatcher
import models
from workers import WebSource
from parsers import HTMLParser


wikipedia = ScrapeModel(
    name='belgian', domain='https://nl.wikipedia.org', num_getters=1, phases=[
    Phase(source_worker=WebSource, parser=HTMLParser, sources=(
        Source(url="https://nl.wikipedia.org/wiki/Lijst_van_Belgische_nationale_regeringen"),),
        templates=[
        Template(name='period', selector='.wikitable.sortable tr', attrs=[
            Attr(name='start', selector='td:nth-of-type(4) a:nth-of-type(2)',
                        func='sel_text', kws={'numbers': True}),
            Attr(name='end', selector='td:nth-of-type(5) a:nth-of-type(2)',
                        func='sel_text', kws={'numbers': True}),
            Attr(name='url', selector='td:nth-of-type(1) a',
                        func='sel_url')
        ], source={'active': False, 'copy_attrs': True})
    ]),
    Phase(source_worker=WebSource, parser=HTMLParser, templates=[
        Template(name='period', selector='table.wikitable:nth-of-type(1) tr', attrs=[
            Attr(name='url', selector='td:nth-of-type(2) a',
                        func='sel_url'),
            Attr(name='party', selector='td:nth-of-type(3)',
                        func='sel_text'),
            Attr(name='role', selector='td:nth-of-type(1)',
                        func='sel_text'),
        ], source={'active': False, 'copy_attrs': True})
    ]),
    Phase(source_worker=WebSource, parser=HTMLParser,  templates=[
        Template(name='politician', db_type='MongoDB', db='belgian_politics',
               table='politicians_extra', attrs=[
            Attr(name='name', selector='#firstHeading', func='sel_text'),
            Attr(name='text', selector='.mw-body-content', func='sel_text'),
            Attr(name='links', selector='.mw-body-content a', func='sel_url'),
        ])])
    ])

disp = Dispatcher()
disp.add_scraper(wikipedia)
disp.run()
