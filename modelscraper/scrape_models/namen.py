from dispatcher import Dispatcher
from components import ScrapeModel, Phase, Template, Attr, Source
from workers import WebSource
from parsers import HTMLParser
import string


meertens = ScrapeModel(
    name='namen', domain='http://www.meertens.knaw.nl/', num_getters=2, phases=[
    Phase(source_worker=WebSource, parser=HTMLParser, sources=(
        Source(url="http://www.meertens.knaw.nl/nvb/naam/begintmet/" + l)
                    for l in ['Aad']), # string.ascii_lowercase),
        templates=[
            Template(
                name='name', selector='tr.data',
                db_type='mongo_db', db='names', table='name_count_test',
                attrs=[
                    Attr(name='name', selector='td:nth-of-type(1)',
                                func='sel_text'),
                    Attr(name='men', selector='td:nth-of-type(2)',
                                func='sel_text', kws={'numbers': True}),
                    Attr(name='women', selector='td:nth-of-type(3)',
                                func='sel_text', kws={'numbers': True}),
                    Attr(name='url', selector='td:nth-of-type(1) a',
                                func='sel_attr', kws={'attr': 'href'},
                                source={'active': False},
                                source_condition={'women': '> 50',
                                                  'men': '> 50'}),
                ]
            ),
            Template(
                name='next_url', selector='.right',
                attrs=[
                    Attr(name='next', selector='abc',  func='sel_attr',
                                kws={'attr': 'href'}, source={'active': True}),
                ])
            ]
    ),
    Phase(source_worker=WebSource, parser=HTMLParser, templates=[
            Template(
                name='name', selector='table.nameinfo', func='update',
                kws={'key': 'name'}, db_type='mongo_db', db='names',
                table='name_count_test',
                attrs=[
                    Attr(name='name', selector='div.name',
                                func='sel_text'),
                    Attr(name='men', func='sel_text',
                                kws={'numbers': True},
                                selector='tr:nth-of-type(2) td:nth-of-type(3)'),
                    Attr(name='men_second', func='sel_text',
                                kws={'numbers': True},
                                selector='tr:nth-of-type(3) td:nth-of-type(3)'),
                    Attr(name='women', func='sel_text',
                                kws={'numbers': True},
                                selector='tr:nth-of-type(6) td:nth-of-type(3)'),
                    Attr(name='women_second', func='sel_text',
                                kws={'numbers': True},
                                selector='tr:nth-of-type(7) td:nth-of-type(3)'),
                ]
            ),
            Template(
                name='data_url', selector='a[href*="absoluut/man/eerstenaam"]',
                attrs=[
                    Attr(name='next', selector='a',  func='sel_attr',
                                kws={'attr': 'href'},
                                source=Source(active=False, attrs=[
                                    Attr(name='sex_name', value='men')
                                ])
                                ),
                ]
            ),
            Template(
                name='data_url', selector='a[href*="absoluut/man/volgnaam"]',
                attrs=[
                    Attr(name='next', selector='a',  func='sel_attr',
                                kws={'attr': 'href'},
                                source=Source(active=False, attrs=[
                                    Attr(name='sex_name',
                                                value='men_second')
                                ])
                                ),
                ]
            ),
            Template(
                name='data_url', selector='a[href*="absoluut/vrouw/eerstenaam"]',
                attrs=[
                    Attr(name='next', selector='a',  func='sel_attr',
                                kws={'attr': 'href'},
                                source=Source(active=False, attrs=[
                                    Attr(name='sex_name', value='women')
                                ])
                                ),
                ]
            ),
            Template(
                name='data_url', selector='a[href*="absoluut/vrouw/volgnaam"]',
                attrs=[
                    Attr(name='next', selector='a',  func='sel_attr',
                                kws={'attr': 'href'},
                                source=Source(active=False, attrs=[
                                    Attr(name='sex_name',
                                                value='women_second')
                                ])
                                ),
                ]
            ),
        ]
    ),
    Phase(source_worker=WebSource, parser=HTMLParser, templates=[
            Template(
                name='history', selector='#content', db_type='mongo_db', db='names',
                table='history2', kws={'key': 'name'}, attrs=[
                    Attr(name='name', selector='div.name', func='sel_text'),
                    Attr(name='years', selector='script', func='sel_js_array',
                                kws={'var_name': 'year_list', 'var_type': int}),
                    Attr(name='values', selector='script', func='sel_js_array',
                                kws={'var_name': 'value_list', 'var_type': float}),
                    Attr(name='step
                ]
            )
            ]
        )
    ]
)

disp = Dispatcher()
disp.add_scraper(meertens)
if __name__ == '__main__':
    disp.run()
