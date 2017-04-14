from modelscraper.dispatcher import Dispatcher

import nu_nl
import metronieuws
import parool
import volkskrant

disp = Dispatcher()
disp.add_scraper([volkskrant.volkskrant])
disp.run()
