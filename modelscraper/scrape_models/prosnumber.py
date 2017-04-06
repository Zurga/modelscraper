from dispatcher import Dispatcher
from models import Attr, Source, Template, Run, ScrapeModel
from workers import WebSource
from parsers import HTMLParser

kinkycookies = {'ckieLegalIds': '4e17b168-5eb9-4c72-b7ee-3e8aebfd963e'}
sexjobscookies = {'algemeneVoorwaardenVersie': '3'}

kinky =ScrapeModel(name='kinky', domain='http://www.kinky.nl/', cookies=kinkycookies, runs=[
    Run(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url='http://www.kinky.nl/sex-afspraken/mannen/default.aspx?pagesize=5000',
               attrs=[Attr(name='sex', value='man')]),
        Source(url='http://www.kinky.nl/sex-afspraken/vrouwen/default.aspx?pagesize=5000',
               attrs=[Attr(name='sex', value='vrouw')]),
        Source(url='http://www.kinky.nl/sex-afspraken/transsexuelen/default.aspx?pagesize=5000',
               attrs=[Attr(name='sex', value='trans')]),
        Source(url='http://www.kinky.nl/sex-afspraken/stellen/default.aspx?pagesize=5000',
               attrs=[Attr(name='sex', value='stellen')]),
        Source(url='http://www.kinky.nl/sex-afspraken/gay/default.aspx?pagesize=5000',
               attrs=[Attr(name='sex', value='gay')]),
    ],
        templates=[
        Template(name='advert', selector='#advertenties > div', db_type='mongo_db', db='kinky', table='adds',
                 attrs=[
                     Attr(name='phone', selector='.quickinfo > span', func='sel_text',
                          kws={'children': True, 'debug':True, 'regex': 'Mijn telefoonnummer: (.*)'}),
                     Attr(name='city', selector='.quickinfo span.country', func='sel_text'),
                     Attr(name='url', selector='.advertentie_kop a', func='sel_attr',
                          kws={'attr': 'href'})
                 ])
        ]),
    ])
sexjobs =ScrapeModel(name='sexjobs', domain='http://www.sexjobs.nl/', cookies=sexjobscookies, runs=[
    Run(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url='http://www.sexjobs.nl/dames-van-plezier/algemeen',
               attrs=[Attr(name='sex', value='vrouw')]),
        Source(url='http://www.sexjobs.nl/dames-van-plezier/thuisontvangst',
               attrs=[Attr(name='sex', value='vrouw')]),
        Source(url='http://www.sexjobs.nl/dames-van-plezier/escort',
               attrs=[Attr(name='sex', value='vrouw')]),
        ], templates=[
            Template(name='url', selector='.advertentie-item', attrs=[
                Attr(name='url', selector='.advertentie-omschrijving > a', func='sel_attr', kws={'attr':'href'},
                     source={'active': False}),
            ]),
            Template(name='pagination', selector='.pagination', attrs=[
                Attr(name='url', selector='a', func='sel_attr', kws={'attr':'href'},
                     source=True),
            ])
        ]),
    Run(source_worker=WebSource, parser=HTMLParser, templates=[
        Template(name='advert', selector='article', db_type='mongo_db', db='sexjobs', table='adds',
                 attrs=[
                     Attr(name='phone', selector='hidden-xs .advertentie-telefoonnummer', func='sel_text',
                          kws={'debug':True}),
                     Attr(name='city', selector='.hidden-xs .advertentie-info tr', func='sel_text',
                          kws={'regex': 'Plaats:\s*(.*)'}),
                     Attr(name='url', selector='.advertentie_kop a', func='sel_attr',
                          kws={'attr': 'href'})
                 ])
        ]),
    ])
d = Dispatcher()
#d.add_scraper(kinky)
d.add_scraper(sexjobs)
d.run()
