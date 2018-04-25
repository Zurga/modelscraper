from modelscraper.components import *
from modelscraper.dispatcher import Dispatcher

temp = Template(
    db_type='MongoDB',
    db='defcon',
    table='companies')

model = ScrapeModel(
    phases=[
        Phase(
            sources=Source.from_db(temp, url='website',
                                   query={'website': {'$ne': None}}),
        )])
d = Dispatcher()
d.add_scraper(model)
d.run()
