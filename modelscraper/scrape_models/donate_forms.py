from dispatcher import Dispatcher
import re
import models
from functions.store_functions import *
from functions.parse_functions import *
from pymongo import MongoClient

client = MongoClient()

info = [{'first_name': 'Tim',
         'last_name': 'de Graaff',
         'zip': '1052VG',
         'number': '14',
         'street': 'Gillis van Ledenberchstraat',
         'city': 'Amsterdam',
         'email': 'tdegraaff@mailinator.com'
         }]

hartstichting = ScrapeModel(name='Hartstichting', domain='hartstichting.nl',
    phases=[
        Phase(getters=
