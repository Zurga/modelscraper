from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
import string


name_count = Attr(func='sel_text', kws={'numbers': True})
name_list = Template(
    name='name_list', selector='tr.data',
    db_type='MongoDB', db='names', table='name_urls',
    attrs=[
        Attr(name='url', selector='td:nth-of-type(1) a',
             func='sel_url', source={'active': False},
             source_condition={'or': {'men': '> 10', 'women': '> 10'}}),
        name_count(name='men', selector='td:nth-of-type(2)'),
        name_count(name='women', selector='td:nth-of-type(3)'),
    ]
)

next_page = Template(
    name='next_url', selector='.right',
    attrs=[Attr(name='next', selector='a',  func='sel_url', source=True)]
)

name_template = Template(
    name='name', db_type='MongoDB', db='names',
    table='name_count', attrs=[
        Attr(name='name', selector='.name', func='sel_text'),
        name_count(name='men',
             selector='tr:nth-of-type(2) td:nth-of-type(3)'),
        name_count(name='men_second',
             selector='tr:nth-of-type(3) td:nth-of-type(3)'),
        name_count(name='women',
             selector='tr:nth-of-type(6) td:nth-of-type(3)'),
        name_count(name='women_second',
             selector='tr:nth-of-type(7) td:nth-of-type(3)'),
    ]
)

data_attr = Attr(name='url', func='sel_url',
                 source=Source(active=False, parent=True,
                 copy_attrs='gender'))
sex_attr = Attr(name='gender')
data_template = Template(name='data_url')

graph_template = Template(
    name='history', selector='#content', db_type='MongoDB', db='names',
    table='history', kws={'key': 'name'}, attrs=[
        Attr(name='name', selector='div.name', func='sel_text'),
        Attr(name='years', selector='script', func='sel_js_array',
             kws={'var_name': 'year_list', 'var_type': int}),
        Attr(name='values', selector='script', func='sel_js_array',
             kws={'var_name': 'value_list', 'var_type': float}),
    ]
)
test = [Source(url='http://www.meertens.knaw.nl/nvb/naam/is/Jim')]
sources = (Source(url="http://www.meertens.knaw.nl/nvb/naam/begintmet/" + l)
                        for l in string.ascii_lowercase)
meertens = ScrapeModel(
    name='namen', domain='http://www.meertens.knaw.nl/', num_getters=2,
    phases=[
        Phase(sources=sources, templates=[name_list, next_page]
        ),
        Phase(templates=[
            name_template,
            data_template(selector='a[href*="absoluut/man/eerstenaam"]',
                          attrs=[data_attr, sex_attr(value='men')]),
            data_template(selector='a[href*="absoluut/man/volgnaam"]',
                          attrs=[data_attr, sex_attr(value='men_second')]),
            data_template(selector='a[href*="absoluut/vrouw/eerstenaam"]',
                          attrs=[data_attr, sex_attr(value='women')]),
            data_template(selector='a[href*="absoluut/vrouw/volgnaam"]',
                          attrs=[data_attr, sex_attr(value='women_second')]),
            ]
        ),
        Phase(templates=[graph_template])
    ]
)
