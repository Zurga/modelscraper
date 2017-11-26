
from dispatcher import Dispatcher
import re
import models
from functions.store_functions import *
from functions.parse_functions import *
from pymongo import MongoClient

client = MongoClient()

autoscout = ScrapeModel(name='autoscout24', domain='autoscout24.nl', num_get=10, phases=[
    Phase(repeat=True,getters=[models.Getter(url='https://labs.volkskrant.nl/api/examens/?action=vote&id=3864')])
])
dis = Dispatcher()
dis.add_scraper(autoscout)
dis.run()
