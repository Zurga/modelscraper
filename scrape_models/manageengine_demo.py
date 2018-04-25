from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from modelscraper.sources import ProgramSource, WebSource
from modelscraper.parsers import TextParser, CSVParser
from scrape_models.objects.networking import ip_phase, port_phase


start = (Source(url='https://www.manageengine.com/products.html?MEtab'),)

demo_template = Template(
    name='demo',
    selector='.all_prod_over',
    db='test',
    db_type='MongoDB',
    table='test',
    attrs=[
        Attr(
            name='url',
            selector='a',
            func='sel_url',
            kws={'regex': 'http[s]?://([\.a-z]*)[\/\?]',
                 'index': 0},
            source={'active': False}
        )
    ]
)

manageengine = ScrapeModel(
    name='manageengine',
    domain='',
    num_getters=1,
    phases=[
        Phase(sources=start, templates=[demo_template]),
        ip_phase,
        port_phase(
    ]
)
