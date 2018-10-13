from modelscraper.components import Scraper, Template, Attr
from modelscraper.sources import FileSource, BrowserSource, WebSource
from modelscraper.parsers import HTMLParser, JSONParser, TextParser, CSVParser
from modelscraper.databases import MongoDB, Sqlite


#Sources
json_test = FileSource(urls=['test/json'])
html = BrowserSource(name='html', urls=['http://google.com'], attrs=[{'test': ['value']}])
#html = FileSource(name='html', urls=['test/html' ], attrs=[{'test': ['value']}])
html2 = FileSource(name='html2')
json_html_nest = FileSource(urls=['test/json_html_nested'])
text_source = FileSource(name='text_source', urls=['test/text'])
csv_source = FileSource(name='csv_source', urls=['test/csv'])


#Databases
test_db = Sqlite(db='test')
test_mongo = MongoDB(db='test')

#Parsers
jsonp = JSONParser()
textp = TextParser()
csvp = CSVParser()
htmlp = HTMLParser()

json_nested = Template(
    source=json_test,
    database=[test_db, test_mongo], table='tst',
    name='json_nested',
    selector=[jsonp.select('html'), htmlp.select('.content')], attrs=[
        Attr(name='url',
             func=htmlp.text(selector='h1', template='partialtest {}'))
    ])

html_functions = Template(
    source=html,
    name='html_functions',
    database=test_mongo, table='html_test',
    dated=True, emits=html2,
    selector=htmlp.select('html'), attrs=[
        Attr(name='table', func=htmlp.table(selector='table')),
        Attr(name='attr', func=htmlp.attr(selector='p', attr='class')),
        Attr(name='url', func=htmlp.url(selector='a')),
        Attr(name='exists', func=htmlp.exists(selector='p', key='Help')),
        Attr(name='js_array', func=htmlp.js_array(selector='script')),
    ])

html2_func = Template(
    source=html2,
    name='html_functions2', parser=HTMLParser,
    database=test_mongo, table='html_test',
    dated=True,
    attrs=[
        Attr(name='table', func=htmlp.table(selector='table')),
        Attr(name='attr', func=htmlp.attr(selector='p', attr='class')),
        Attr(name='url', func=htmlp.url(selector='a')),
        Attr(name='exists', func=htmlp.exists(selector='p', key='Help')),
        Attr(name='js_array', func=htmlp.js_array(selector='script')),
    ])

'''
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
'''


test = Scraper(
    name='test', domain='http://localhost:9999',
    templates=[html_functions, html2_func]
    , logfile='test.log')
