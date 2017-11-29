from dispatcher import Dispatcher
import re
import models
from functions.store_functions import *
from functions.parse_functions import *
from pymongo import MongoClient

cl = MongoClient()
db = cl.nos_nl
urls = (art['url'] for art in db.headlines.find({'url': {'$exists': 'true'}}))
nu = ScrapeModel(name='nos.nl', domain='http://nos.nl', num_getters=41, phases=[
    Phase(getters=(
        Getter(url="{}".format(url),
                      attrs=[Attr(name='category', value='binnenland'),
                             Attr(name='url', value=url)]
                      )
                      for url in urls),
        templates=[
            Template(
                name='headline', selector='article.article',
                store=StoreObject(func=store_mongo,
                                         kws={'db': 'nos_nl',
                                              'collection': 'articles'}),
                attrs=[
                    Attr(name='title', selector='h1', func=sel_text),
                    Attr(name='text', selector='.article_textwrap', func=sel_text),
                    Attr(name='publish', selector='time:nth-of-type(1)', func=sel_attr,
                                kws={'attr': 'datetime'}),
                    Attr(name='edit', selector='time:nth-of-type(2)', func=sel_attr,
                                kws={'attr': 'datetime'}),
                ]
            )
        ]
    )
]
)

disp = Dispatcher()
disp.add_scraper(nu)
disp.run()
