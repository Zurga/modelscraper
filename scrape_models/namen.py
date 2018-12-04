from modelscraper import Scraper, Model, Attr, WebSource, MongoDB, HTMLParser
import string


name_list_source = WebSource(
    urls=["http://www.meertens.knaw.nl/nvb/naam/begintmet/" + l for l in
          string.ascii_lowercase],
    test_urls=['http://www.meertens.knaw.nl/nvb/naam/begintmet/a'])
name_source = WebSource(
    test_urls=['http://www.meertens.knaw.nl/nvb/populariteit/naam/A'])
name_history_source = WebSource()
data_source = WebSource()
database = MongoDB(db='names')
parser = HTMLParser()


def greater_then_10(x):
    return x > 10 if isinstance(x, int) else False


name_list = Model(
    source=name_list_source,
    name='name_list', selector=parser.select('tr.data'),
    database=database, table='name_urls',
    attrs=[
        Attr(name='url', func=parser.url(selector='td:nth-of-type(1) a'),
             emits=name_source,
             source_condition={'or': {'men': greater_then_10, 'women':
                                      greater_then_10}}),
        Attr(name='men', func=parser.text(selector='td:nth-of-type(2)',
                                          numbers=True)),
        Attr(name='women', func=parser.text(selector='td:nth-of-type(3)',
                                            numbers=True)),
    ]
)

next_page = Model(
    source=name_list_source,
    name='next_url', selector=parser.select('.right a'),
    attrs=[Attr(name='next', func=parser.url(),
                emits=name_list_source)]
)

name_template = Model(
    source=name_source,
    name='name',
    database=database,
    table='name_count', attrs=[
        Attr(name='name', func=parser.text(selector='.name')),
        Attr(name='men', func=parser.text(
            selector='tr:nth-of-type(2) td:nth-of-type(3)',
            numbers=True)),
        Attr(name='men_second', func=parser.text(
            selector='tr:nth-of-type(3) td:nth-of-type(3)',
            numbers=True)),
        Attr(name='women', func=parser.text(
            selector='tr:nth-of-type(6) td:nth-of-type(3)',
            numbers=True)),
        Attr(name='women_second', func=parser.text(
            selector='tr:nth-of-type(7) td:nth-of-type(3)',
            numbers=True)),
    ]
)

data_attr = Attr(name='url', func=parser.url(), emits=data_source)
sex_attr = Attr(name='gender', transfers=True)

men_first = Model(name='men_first', source=name_source,
                  selector=parser.select('a[href*="absoluut/man/eerstenaam"]'),
                  attrs=[data_attr, sex_attr(value='men')])
men_second = Model(name='men_second', source=name_source,
                   selector=parser.select('a[href*="absoluut/man/volgnaam"]'),
                   attrs=[data_attr, sex_attr(value='men_second')])
women_first = Model(name='women_first', source=name_source,
                    selector=parser.select('a[href*="absoluut/vrouw/eerstenaam"]'),
                    attrs=[data_attr, sex_attr(value='women')])
women_second = Model(name='women_second', source=name_source,
                     selector=parser.select('a[href*="absoluut/vrouw/volgnaam"]'),
                     attrs=[data_attr, sex_attr(value='women_second')])

graph_template = Model(
    source=data_source,
    name='history', selector=parser.select('#content'),
    database=database,
    debug=True,
    table='history',  attrs=[
        Attr(name='name', func=parser.text(selector='div.name')),
        Attr(name='years', multiple=True, func=parser.js_array(
            selector='script', var_name='year_list', var_type=int)),
        Attr(name='values', multiple=True, func=parser.js_array(
            selector='script', var_name='year_list', var_type=float)),
        Attr(name='gender', from_source=True),
    ]
)
meertens = Scraper(
    name='namen',
    models=[name_list, next_page, men_first, men_second, women_first,
            women_second, graph_template]
)
