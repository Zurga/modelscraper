# TODO Set the right classes for the websites.
from dispatcher import Dispatcher
from components import Attr, Source, HTMLObject, Phase, ScrapeModel, Follow

kinky =ScrapeModel(name='kinky', domain='kinky.nl', phases=[
    Phase(source=[Source(url='http://kinky.nl/sex-afspraken/vrouwen/default.aspx?pagesize=4500')],
        templates=[Template(name='advert', selector='.advertentie_kop > a',
                 attrs=[Attr(name='url', source={'active': False})])
        ]),
    Phase(templates=[
        Template(name='advert', selector='.advertentie_kop > a', db='kinky.nl', table='adverts',
                Attr(name='add_text', func= 'sel_text', selector='description p'),
                Attr(name='possibilities', func= 'sel_text', selector= '.possibilities li'),
                Attr(name='update', func= 'sel_text', selector='update'),
                Attr(name='town', func= 'sel_text', selector= '.naw div', kws={'regex': '.*Plaats: ([A-z]*);'}),
                Attr(name='work_area', func= 'sel_text', selector='naw div', kws={'regex': '.*Werkgebied: '}),
                Attr(name='prices', func= 'sel_text', selector='.prizes td:nth-of-type(2)'),
                Attr(name='pictures', func= 'sel_attr', selector='.galleryRow img', kws={'attr': 'src'}),
                Attr(name='phone', selector='.mainprofile .webbutton span', func='sel_text'),
                Attr(name='name', selector='h1.title', func='sel_text'),
                    '__reg__age': ['.naw div', '.*Leeftijd: (\d\d)'],
                    '__reg__length': ['.naw div', '.*Lengte: (\d\d\d)'],
                    '__reg__hair_color': ['.naw div', '.*Kleur haar: ([a-z]*);'],
                    '__reg__build': ['.naw div', '.*Lichaamsbouw: ([A-z]*);'],
                    '__reg__looks': ['.naw div', '.*Uiterlijk: ([A-z]*);'],
                ,
            ,
        ,
        'start': [
            'meta': {
                'sex': 'female',
                'category': 'common',
                ,
                'url': '',
                'active': True,
             ,
            'meta': {
                'sex': 'male',
                'category': 'common',
                ,
                'url': 'sex-afspraken/mannen/default.aspx?pagesize=4000',
                'active': False,
             ,
        ],
        'list_url': 'http://www.kinky.nl/',
        'object_url': 'http://www.kinky.nl/mobiel',
        'timestamp': True,
    ,
    'sexjobs':
        'css':
            'list_class': 'td.b a',
            'sections':
                'advert':
                    'add_text': '.excerpt',
                    'update': '#col div:nth-of-type(1)',
                    '__href__pictures': '.ad-detail-images a',
                    '__reg__phone': ['.ad-detail-pic .phone', r'(\d+)'],
                    '__reg__viewed': ['div.aantal', r'(\d+'],
                ,
                'personal':
                    'name': '.below .naam',
                    '__reg__phone': ['.ad-detail-pic .phone', r'(\d+)'],
                    '__reg__member_since': ['.sub-menu li:nth-of-type(1)',
                                            r'Lid sinds' + line],
                ,
            ,
        ,
        'start': [
            'sex': 'female',
                'url': 'sexjobs/amateur-hoeren/algemeen',
                'category': 'common',
                'active': False,

        ],
        'iter_class': '.voet > span > a',
        'iter_stop': 1,
        'list_url': 'http://sexjobs.nl/',
        'object_url': 'http://m.sexjobs.nl/',
        'range_mod': -2,
        'timestamp': True,
        ,
    'speurders':
        'object_url': 'http://www.speurders.nl/',
        'list_url': 'http://www.speurders.nl/',
        'iter_stop': 2,
        '__iter_class': 'a.pjax',
        'range_mod': -1,
        'start': [
            'meta': {
                'sex': 'female',
                'category': 'common',
                ,
                # 'url': 'overzicht/erotiek/contact-escort-en-thuis-ontvangst/',
                'url': 'overzicht/banen/marketing/',
                'active': False,

        ],
        'css':
            'list_class': '.pagination li:last-child a',
            'sections':
                'add':
                    'add_text': '.user_content',
                    'price': '.standout-xxlarge',
                    'Plaatsnaam': '.block .half-bottom-margin > span > strong',
                    'name': '.block .half-bottom-margin > span > strong',
                    '__reg__viewed': ['span.small', '(\d*) x'],
                ,
            ,
        ,


