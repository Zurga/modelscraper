from dispatcher import Dispatcher
from workers.http_worker import WebSource
from models import ScrapeModel
from models import Run
from models import Attr
from models import Template
from models import Source
from scrape_models import eufa


disp = Dispatcher()
disp.add_scraper(eufa.eufa)
disp.run()

