from dispatcher import Dispatcher
import models
from workers import WebSource
from parsers import HTMLParser


wikipedia = models.ScrapeModel(
    name='belgian', domain='https://nl.wikipedia.org', num_getters=1, runs=[
    models.Run(source_worker=WebSource, parser=HTMLParser, sources=(
        models.Source(url="https://nl.wikipedia.org/wiki/Lijst_van_Belgische_nationale_regeringen"),),
        templates=[
        models.Template(name='period', selector='.wikitable.sortable tr', attrs=[
            models.Attr(name='start', selector='td:nth-of-type(4) a:nth-of-type(2)',
                        func='sel_text', kws={'numbers': True}),
            models.Attr(name='end', selector='td:nth-of-type(5) a:nth-of-type(2)',
                        func='sel_text', kws={'numbers': True}),
            models.Attr(name='url', selector='td:nth-of-type(1) a',
                        func='sel_url')
        ], source={'active': False, 'copy_attrs': True})
    ]),
    models.Run(source_worker=WebSource, parser=HTMLParser, templates=[
        models.Template(name='period', selector='table.wikitable:nth-of-type(1) tr', attrs=[
            models.Attr(name='url', selector='td:nth-of-type(2) a',
                        func='sel_url'),
            models.Attr(name='party', selector='td:nth-of-type(3)',
                        func='sel_text'),
            models.Attr(name='role', selector='td:nth-of-type(1)',
                        func='sel_text'),
        ], source={'active': False, 'copy_attrs': True})
    ]),
    models.Run(source_worker=WebSource, parser=HTMLParser,  templates=[
        models.Template(name='politician', db_type='mongo_db', db='belgian_politics',
               table='politicians_extra', attrs=[
            models.Attr(name='name', selector='#firstHeading', func='sel_text'),
            models.Attr(name='text', selector='.mw-body-content', func='sel_text'),
            models.Attr(name='links', selector='.mw-body-content a', func='sel_url'),
        ])])
    ])

disp = Dispatcher()
disp.add_scraper(wikipedia)
disp.run()
