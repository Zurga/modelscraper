from dispatcher import Dispatcher
import models
from workers import WebSource
from parsers import HTMLParser


wikipedia = ScrapeModel(
    name='belgian', domain='https://nl.wikipedia.org', num_getters=1, phases=[
    Phase(source_worker=WebSource, parser=HTMLParser, sources=(
        Source(url="https://nl.wikipedia.org/wiki/Lijst_van_voorzitters_van_de_Kamer_van_Volksvertegenwoordigers"),),
        templates=[
            Template(
                name='year', selector='',
                attrs=[
                    Attr(name='url', selector='a[href*="Kamer_van_Volksvertegenwoordigers_(samenstelling"]',
                                func='sel_url', source={'active': False}),
                ]
            )]
    ),
    Phase(source_worker=WebSource, parser=HTMLParser, templates=[
        Template(name='period', db_type='MongoDB', db='belgian_politics',
               table='politicians_per_period', attrs=[
            Attr(name='start', selector='title', func='sel_text', kws={'regex': '(\d+)-\d+',
                                                                              'numbers': True}),
            Attr(name='end', selector='title', func='sel_text', kws={'regex': '\d+-(\d+)',
                                                                            'numbers': True}),
            # Attr(name='changes', selector='(h2 > #Samenstelling) ~ table'),
            Attr(name='members', selector='.wikitable.sortable tr td:nth-of-type(1) a',
                        func='sel_url'),
        ]),
        Template(name='politician', selector='.wikitable.sortable tr', attrs=[
            Attr(name='url', selector='td:nth-of-type(1) a',
                        func='sel_url'),
            Attr(name='party', selector='td:nth-of-type(2)',
                        func='sel_text'),
            Attr(name='district', selector='td:nth-of-type(3)',
                        func='sel_text'),
            Attr(name='language_group', selector='td:nth-of-type(4)',
                        func='sel_text'),
            Attr(name='remarks', selector='td:last-of-type',
                        func='sel_text'),
        ], source={'active': False, 'copy_attrs': True})
    ]),
    Phase(source_worker=WebSource, parser=HTMLParser,  templates=[
        Template(name='politician', db_type='MongoDB', db='belgian_politics',
               table='politicians', attrs=[
            Attr(name='name', selector='#firstHeading', func='sel_text'),
            Attr(name='text', selector='.mw-body-content', func='sel_text'),
            Attr(name='links', selector='.mw-body-content a', func='sel_url'),
        ])])
    ])

disp = Dispatcher()
disp.add_scraper(wikipedia)
disp.run()
