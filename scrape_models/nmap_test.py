from modelscraper.components import Scraper, Model, Attr
from modelscraper.sources import ProgramSource
from modelscraper.databases import MongoDB


nmap_source = ProgramSource(urls=['localhost'], func='nmap -oX - {}')

port_template = Model(
    source=nmap_source,
    name='ports', selector='port',
    database=MongoDB('nmap'),
    table='ports', attrs=(
    Attr(name='portnumber', func='sel_attr',
         kws={'attr': 'portid'}),
    Attr(name='state', selector='state', func='sel_attr',
         kws={'attr': 'state'}),
    Attr(name='service', selector='service', func='sel_attr',
         kws={'attr': 'name'})))
nmap = Scraper(name='nmap_test', models=[port_template])
