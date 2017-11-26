from dispatcher import Dispatcher
from components import ScrapeModel, Phase, Template, Attr, Source
from pymongo import MongoClient
from workers import WebSource
from parsers import HTMLParser


cl = MongoClient()
db = cl.gsmhelpdesk_nummerreeksen
col = db.number_range

gsmhelpdesk_nummerreeksen = ScrapeModel(name='gsmhelpdesk_nummerreeksen', domain='http://www.gsmhelpdesk.nl/', num_getters=2,
    phases=[

    Phase(source_worker=WebSource, parser=HTMLParser, sources=[
        Source(url="http://www.gsmhelpdesk.nl/helpdesk/30/nummerreeksen"),
    ],
    templates=(
        Template(
            name='number_range', selector='tr',
            db_type='mongo_db', db='gsmhelpdesk_nummerreeksen', table='number_range',
            attrs=(
                Attr(name='start', selector='td:nth-of-type(1)',
                            func='sel_text', kws={'numbers': True}),
                Attr(name='end', selector='td:nth-of-type(2)',
                            func='sel_text', kws={'numbers': True}),
                )
            ),
        )
    ),
    ]
)

disp = Dispatcher()
disp.add_scraper(gsmhelpdesk_nummerreeksen)
disp.run()
