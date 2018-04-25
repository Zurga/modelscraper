from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from modelscraper.sources import FileSource
from modelscraper.parsers import HTMLParser, JSONParser
from modelscraper.databases import MongoDB
import http.server


json_test = Source(url='test/json')
html = Source(url='test/html')

json_nested = Template(
    name='json_nested', parser=[JSONParser, HTMLParser],
    db='test', db_type='MongoDB', table='tst',
    selector=['html', '.content'], attrs=[
        Attr(name='header', selector='h1', func='sel_text')
    ])

json_html_nest = Source(url='test/json_html_nested')


test = ScrapeModel(
    name='test', domain='http://localhost:9999',
    phases=[
        Phase(sources=[json_html_nest], source_worker=FileSource,
              templates=[json_nested])
    ])
