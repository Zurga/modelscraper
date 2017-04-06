from dispatcher import Dispatcher
import re
import models
from functions.store_functions import *
from functions.parse_functions import *
from pymongo import MongoClient

youtube = models.ScrapeModel(name='youtube_history', domain='youtube.com', runs=[
    models.Run(getters=[models.Getter(url='sl
