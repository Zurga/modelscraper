from dispatcher import Dispatcher
from workers import WebSource
from parsers import HTMLParser
import string
from components import ScrapeModel, Source, Phase, Attr, Template

paradiso = ScrapeModel(name='paradiso', domain='https://paradiso.nl', phases=[
    Phase(source_worker=WebSource, sources=[Source(url='https://paradiso.nl/web/Agenda.htm')], parser=HTMLParser,
        templates=[Template(name='event_link', selector='a.event-link', attrs=[
            Attr(name='url', func='sel_attr', kws={'attr': 'href'}, source={'active': False})
            ])
        ]),
    Phase(templates=[
        Template(name='event', db_type='MongoDB', db='paradiso', table='events',
                attrs=[
                    Attr(name='name', selector='meta[name=evenementts]',
                        func='sel_attr', kws={'attr': 'content'}),
                    Attr(name='date', selector='meta[name=evenementts]',
                        func='parse_attr', kws={'attr': 'content'}),
                    Attr(name='time', selector='meta[name=evenementtijd]',
                        func='parse_attr', kws={'attr': 'content'}),
                    Attr(name='price', selector='.info p', func='parse_text',
                        kws={'regex': '(\d+,\d*)'}),
                ])
            ])
    ])

disp = Dispatcher()
disp.add_scraper(paradiso)
if __name__ == '__main__':
    disp.run()
'''
Attr(name='address', func='parse_meta', 'selector', 'itemprop', 'streetAddress'],
'__meta__name': ['meta', 'property', 'og:title'],
'__href__links': '.linklist a',
'__reg__opener': ['.info h2', 'Voorprogramma: (.*)'],
{'url': 'web/Archief/2006.htm',
    'active': True,
    },
{'url': 'web/Archief/2007.htm',
    'active': True,
    },
{'url': 'web/Archief/2008.htm',
    'active': True,
    },
{'url': 'web/Archief/2009.htm',
    'active': True,
    },
{'url': 'web/Archief/2010.htm',
    'active': True,
    },
{'url': 'web/Archief/2011.htm',
    'active': True,
    },
{'url': 'web/Archief/2012.htm',
    'active': True,
    },
{'url': 'web/Archief/2013.htm',
    'active': True,
    },
{'url': 'web/Archief/2014.htm',
    'active': True,
    },
{'url': 'web/Archief/2015.htm',
    'active': True,
    },
'''
