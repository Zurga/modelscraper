from components import ScrapeModel, Phase, Source, Template, Attr
from dispatcher import Dispatcher
from workers import WebSource
from parsers import HTMLParser


funda = ScrapeModel(name='funda.nl', domain='http://funda.nl', num_sources=1, phases=[
    Phase(parser=HTMLParser, source_worker=WebSource, sources=[
        Source(url='http://funda.nl/huur/amsterdam/woonhuis/'),
        Source(url='http://funda.nl/huur/amsterdam/appartement/'),
        Source(url='http://funda.nl/koop/amsterdam/woonhuis/'),
        Source(url='http://funda.nl/koop/amsterdam/appartement'),
    ],
        templates=[
            Template(name='house', selector='.search-result',
                     db_type='MongoDB', db='funda', table='for_hire',
                     attrs=[
                         Attr(name='price', selector='.search-result-price',
                              func='sel_text', kws={'numbers': True}),

                         Attr(name='street', selector='.search-result-title',
                              func='sel_text'),

                         Attr(name='realtor', selector='.realtor',
                              func='sel_text'),

                         Attr(name='rooms', selector='.search-result-info',
                              func='sel_text',
                              kws={'regex': '(\d+) kamers', 'numbers': True}),

                         Attr(name='zip', selector='.search-result-subtitle',
                              func='sel_text', kws={'regex': '(\d{4} \w{2})'}),

                         Attr(name='city', func='sel_text',
                              selector='.search-result-subtitle',
                              kws={'regex': '\d{4} \w{2} (\w+)'}),

                         Attr(name='living_area', func='sel_text',
                              selector='.search-result-info span[title="Woonoppervlakte"]',
                              kws={'regex': '(\d+)', 'numbers': True}),

                         Attr(name='meeting_url', selector='.search-result-header a',
                              func='sel_attr', kws={'attr': 'href'},
                              source={'src_template': '{}bezichtiging/', 'active': False}),
            ]),
            Template(selector='.pagination', attrs=[
                Attr(name='url', selector='a', func='sel_attr', kws={'attr': 'href'},
                        # source=Source()
                            )])
        ]),
    Phase(parser=HTMLParser, source_worker=WebSource, active=False, templates=[
        Template(name='bezichtiging', selector='.makelaars-contact-form', attrs=[
            Attr(name='__RequestVerificationToken',
                 selector='input[name="__RequestVerificationToken"]', func='sel_attr',
                 kws={'attr': 'value'}),
            Attr(name='url', selector='form', func='sel_attr', kws={'attr': 'action'}),
        ], source=Source(method='post', active=False, duplicate=True,
                         data={'Day': '',
                               'DayPart': '',
                               'Opmerking': '',
                               'Aanhef': 'Dhr',
                               'Naam': 'Henk de Vries',
                               'Email': 'henkdevries@mailinator.com',
                               'ConfirmEmail': '',
                               'Telefoon': '0205566206',
                               }))])
])

disp = Dispatcher()
disp.add_scraper(funda)
disp.run()
