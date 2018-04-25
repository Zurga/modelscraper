from modelscraper.dispatcher import Dispatcher
from modelscraper.components import ScrapeModel, Phase, Template, Attr, Source
from pymongo import MongoClient
import string


start_url = Source(url='http://www.startpagina.nl/dochters/')
sub_page_url = Attr(name='sub_page', func='sel_url', source={'active': False,
                                                             'parent': True})
sub_page_name = Attr(name='pagename', func='sel_text')

category_temp = Template(name='sub_page',
                         selector='.sections a',
                         db='startpagina',
                         table='subpages',
                         db_type='MongoDB',
                         attrs=(sub_page_url,
                                sub_page_name))

website_url = Attr(name='url', func='sel_url')
website_name = Attr(name='name', func='sel_text')

website_temp = Template(name='website',
                        selector='#columns a',
                        db='startpagina',
                        table='websites',
                        db_type='MongoDB',
                        attrs=(website_url, website_name))

model = ScrapeModel(name='startpagina', domain='http://www.startpagina.nl',
                    phases=[
                        Phase(n_workers=3, sources=[start_url],
                            templates=[category_temp]),
                        Phase(n_workers=3, templates=[website_temp])
                    ])

d = Dispatcher()
d.add_scraper(model)
d.run()
