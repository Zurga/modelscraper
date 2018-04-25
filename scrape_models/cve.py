from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from modelscraper.sources import ProgramSource, WebSource
from modelscraper.parsers import JSONParser, TextParser
import datetime


now = str(datetime.datetime.now()).replace('-', '')[:8]
JSON_URL = 'https://static.nvd.nist.gov/feeds/json/cve/1.0/nvdcve-1.0-{}.json.zip'
JSON_URL = 'http://0.0.0.0:8000/nvdcve-1.0-{}.json'

years = range(2002, datetime.datetime.now().year)
# years = [2002]
cve_source = (Source(url=JSON_URL.format(year), compression='',
                     json_key='CVE_Items') for year in years)

meta_template = Template(
    name='meta', db='defcon', table='cve_meta', db_type='MongoDB', attrs=[
    Attr(name='last_modified', func='sel_text',
         kws={'regex': 'lastModifiedDate:(.*)'},
         source=cve_source)])

cve_template = Template(
    name='meta', db='defcon', table='cve', db_type='MongoDB', #func='update',
    #kws={'key': 'id'},
    attrs=[
        Attr(name='id', func='sel_text',
             selector=['cve', 'CVE_data_meta', 'ID']),
        Attr(name='cpes', func='sel_text',
             selector=['configurations', 'nodes', 'cpe', 'cpe23Uri']),
        Attr(name='affects', func='sel_dict',
             selector=['cve', 'affects']),
        Attr(name='problem_type', func='sel_text',
             selector=['cve', 'problemtype', 'problemtype_data', 'description',
                       'value']),
        Attr(name='description', func='sel_dict',
             selector=['cve', 'description', 'description_data', 'value']),
        Attr(name='impact', func='sel_dict',
             selector=['impact'])
    ])

cve = ScrapeModel(name='CVE', domain='static.nvd.nist.gov', phases=[
    Phase(sources=cve_source, parser=JSONParser, templates=[cve_template])
])
