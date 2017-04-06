from dispatcher import Dispatcher
import models
from workers import WebSource
from parsers import HTMLParser


wikipedia = models.ScrapeModel(
    name='belgian', domain='https://nl.wikipedia.org', num_getters=1, runs=[
    models.Run(source_worker=WebSource, parser=HTMLParser, sources=(
        models.Source(url="https://nl.wikipedia.org/wiki/Lijst_van_voorzitters_van_de_Kamer_van_Volksvertegenwoordigers"),),
        templates=[
            models.Template(
                name='year', selector='',
                attrs=[
                    models.Attr(name='url', selector='a[href*="Kamer_van_Volksvertegenwoordigers_(samenstelling"]',
                                func='sel_url', source={'active': False}),
                ]
            )]
    ),
    models.Run(source_worker=WebSource, parser=HTMLParser, templates=[
        models.Template(name='period', db_type='mongo_db', db='belgian_politics',
               table='politicians_per_period', attrs=[
            models.Attr(name='start', selector='title', func='sel_text', kws={'regex': '(\d+)-\d+',
                                                                              'numbers': True}),
            models.Attr(name='end', selector='title', func='sel_text', kws={'regex': '\d+-(\d+)',
                                                                            'numbers': True}),
            # models.Attr(name='changes', selector='(h2 > #Samenstelling) ~ table'),
            models.Attr(name='members', selector='.wikitable.sortable tr td:nth-of-type(1) a',
                        func='sel_url'),
        ]),
        models.Template(name='politician', selector='.wikitable.sortable tr', attrs=[
            models.Attr(name='url', selector='td:nth-of-type(1) a',
                        func='sel_url'),
            models.Attr(name='party', selector='td:nth-of-type(2)',
                        func='sel_text'),
            models.Attr(name='district', selector='td:nth-of-type(3)',
                        func='sel_text'),
            models.Attr(name='language_group', selector='td:nth-of-type(4)',
                        func='sel_text'),
            models.Attr(name='remarks', selector='td:last-of-type',
                        func='sel_text'),
        ], source={'active': False, 'copy_attrs': True})
    ]),
    models.Run(source_worker=WebSource, parser=HTMLParser,  templates=[
        models.Template(name='politician', db_type='mongo_db', db='belgian_politics',
               table='politicians', attrs=[
            models.Attr(name='name', selector='#firstHeading', func='sel_text'),
            models.Attr(name='text', selector='.mw-body-content', func='sel_text'),
            models.Attr(name='links', selector='.mw-body-content a', func='sel_url'),
        ])])
    ])

disp = Dispatcher()
disp.add_scraper(wikipedia)
disp.run()
