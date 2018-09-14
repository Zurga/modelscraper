from modelscraper.components import ScrapeModel, Template, Attr
from modelscraper.sources import FileSource
from modelscraper.parsers import HTMLParser, JSONParser, TextParser, CSVParser
from modelscraper.databases import MongoDB, Sqlite
import http.server


json_test = FileSource(urls=['test/json'])
html = FileSource(name='html', urls=['test/html'], attrs=[{'test': ['value']}])
html2 = FileSource(name='html2')
json_html_nest = FileSource(urls=['test/json_html_nested'])
text_source = FileSource(name='text_source', urls=['test/text'])
csv_source = FileSource(name='csv_source', urls=['test/csv'])
test_db = Sqlite(db='test')
test_mongo = MongoDB(db='test')

json_nested = Template(
    source=json_test,
    database=[test_db, test_mongo], table='tst',
    name='json_nested', parser=[JSONParser, HTMLParser],
    selector=['html', '.content'], attrs=[
        Attr(name='url', selector='h1', func=['sel_text', 'sel_text'],
             kws=[{}, {'template': 'partialtest {}'}]),
    ])

html_functions = Template(
    source=html,
    name='html_functions', parser=HTMLParser,
    database=test_db, table='html_test',
    dated=True,
    selector='html', attrs=[
        Attr(name='table' , selector='table', func='sel_table'),
        Attr(name='attr' , selector='p', func='sel_attr',
             kws={'attr': 'class'}),
        Attr(name='url' , selector='a', func='sel_url', emits=html2),
        Attr(name='exists', selector='p', func='sel_exists', kws={'key': 'Help'}),
        Attr(name='js_array', selector='script', func='sel_js_array'),
    ])

html2_func = Template(
    source=html2,
    name='html_functions2', parser=HTMLParser,
    database=test_db, table='html_test',
    dated=True,
    selector='html', attrs=[
        Attr(name='table' , selector='table', func='sel_table'),
        Attr(name='attr' , selector='p', func='sel_attr',
             kws={'attr': 'class'}),
        Attr(name='url' , selector='a', func='sel_url' ),
        Attr(name='exists', selector='p', func='sel_exists', kws={'key': 'Help'}),
        Attr(name='js_array', selector='script', func='sel_js_array'),
    ])

text_functions = Template(
    source=text_source,
    name='text_functions', parser=TextParser,
    database=test_db, table='text_test',
    dated=True,
    selector='', attrs=[
        Attr(name='table' , selector='#', func='sel_text'),
    ])

csv_functions = Template(
    source=csv_source,
    name='csv_functions', parser=CSVParser,
    database=test_db, table='csv_test',
    dated=True,
    selector=slice(1, 5), attrs=[
        Attr(name='col2', selector=2, func='sel_text'),
        Attr(name='col1' , selector=1, func='sel_text'),
    ])


test = ScrapeModel(
    name='test', domain='http://localhost:9999',
    templates=[html_functions, html2_func]
    , logfile='test.log')
