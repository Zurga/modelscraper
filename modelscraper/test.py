from dispatcher import Dispatcher
from workers.http_worker import WebSource
from components import ScrapeModel
from components import Phase
from components import Attr
from components import Template
from components import Source
from scrape_components import eufa


disp = Dispatcher()
disp.add_scraper(eufa.eufa)
disp.run()

