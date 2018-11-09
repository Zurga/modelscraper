from modelscraper.components import Scraper, Model, Attr
from modelscraper.sources import ProgramSource
from modelscraper.parsers import HTMLParser
from modelscraper.databases import MongoDB


nmap_source = ProgramSource(urls=['localhost'], test_urls=['localhost'], func='nmap -oX - {}')
parser = HTMLParser()


port_template = Model(
    source=nmap_source,
    name='ports', selector=parser.select('port'),
    database=MongoDB(db='nmap'),
    table='ports', attrs=(
    Attr(name='portnumber', func=parser.attr(attr='portid')),
    Attr(name='state', func=parser.attr(selector='state', attr='state')),
    Attr(name='service', func=parser.attr(selector='service',attr='name')))
)

nmap = Scraper(name='nmap_test', models=[port_template])
