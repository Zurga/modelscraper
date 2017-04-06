from dispatcher import Dispatcher
import re
from models import models
from pymongo import MongoClient


# models.Source(url="http://www.nu.nl/block/html/articlelist?footer=ajax&section=economie&limit=20&offset={}&show_tabs=0".
#                 format(i)) for i in range(0, 2000000, 20)
url = "http://www.nu.nl/block/html/articlelist?footer=ajax&section=buitenland&limit=20&offset={}&show_tabs=0"
sources = (models.Source(url=url.format(i),
                         attrs=[models.Attr(name='category',
                                            value='buitenland')])
           for i in range(0, 2000000, 20))
templates = models.Template(
    name='headline',
    selector='li',
    db='nu_nl',
    db_type='mongo_db',
    table='headlines',
    attrs=[
        models.Attr(name='url', selector='a', func='sel_attr',
                    kws={'attr': 'href'}),
        models.Attr(name='title', selector='.title', func='sel_text'),
        models.Attr(name='excerpt', selector='.excerpt', func='sel_text'),
    ]
    )

nu = models.ScrapeModel(name='nu.nl', domain='http://nu.nl', runs=[
    models.Run(sources=sources, templates=[templates ])
])

disp = Dispatcher()
disp.add_scraper(nu)
disp.run()
