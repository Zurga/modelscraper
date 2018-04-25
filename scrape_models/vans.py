from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from scrape_models.objects import occassions


sources = [Source(url='http://ww4.autoscout24.nl/?atype=B&mmvco=0&cy=NL&ustate=N%2CU&fromhome=1&intcidm=HP-Searchmask-Button&dtr=s&results=20')]
autoscout = ScrapeModel(
    name='autoscout24',
    domain='autoscout24.nl',
    phases=[
        Phase(sources=sources,
              templates=[occassions.autoscout_template]),
])
