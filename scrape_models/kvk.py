from dispatcher import Dispatcher
import models
from functions.store_functions import *
from functions.parse_functions import *
from pymongo import MongoClient
import datetime
import string

letters = [s for s in string.ascii_lowercase]

kvk = ScrapeModel(name='kvk', domain='http://www.kvk.nl', phases=[
    model.Phase(getter=(
        Getter(url='http://zoeken.kvk.nl/search.ashx?callback=&handelsnaam=%s&kvknummer=&straat=&postcode=&huisnummer=&plaats=&hoofdvestiging=true&rechtspersoon=true&nevenvestiging=false&zoekvervallen=0&zoekuitgeschreven=1&start=0&initial=0&searchfield=uitgebreidzoeken' % (l))
        l for l in letters),
        templates=[
            Template(selector='ul.results li.type1', name='resultaat')


