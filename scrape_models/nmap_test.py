from modelscraper.dispatcher import Dispatcher
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from modelscraper.sources import ProgramSource


port_template = Template(
    name='ports', selector='port', db_type='MongoDB', db='ports',
    table='ports', attrs=(
    Attr(name='portnumber', func='sel_attr',
         kws={'attr': 'portid'}),
    Attr(name='state', selector='state', func='sel_attr',
         kws={'attr': 'state'}),
    Attr(name='service', selector='service', func='sel_attr',
         kws={'attr': 'name'})))
nmap = ScrapeModel(name='nmap_test', domain='', phases=[
    Phase(sources=(Source(url='nmap -oX - duwo.multiposs.nl'),),
        templates=[port_template], source_worker=ProgramSource)])

disp = Dispatcher()
disp.add_scraper(nmap)
disp.run()
