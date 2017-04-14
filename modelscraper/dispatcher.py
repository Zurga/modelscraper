from . import workers
from multiprocessing import Queue
#from queue import Queue
from . import databases
from collections import defaultdict


class Dispatcher:
    def __init__(self):
        self.scrapers = {}

        self.store_q = Queue()
        self.results = []
        self.store_threads = []

    def run(self):
#        try:
        for scraper in self.scrapers.values():
            scraper.start()
            print('started', scraper.name)

        for scraper in self.scrapers.values():
            scraper.join()

        print('scraper joined')
        for store in self.store_threads:
            store.join()

        for scraper in self.scrapers.values():
            while scraper.awaiting and scraper.source_q.empty():
                url = input('url: ')
                scraper.add_source(url)

#        except KeyboardInterrupt:

        # TODO fix that the seen urls go to the databases.
        print('joined')

        self.store_q.put(None)

    def add_scraper(self, models):
        if type(models) != list:
            models = [models]

        db_threads = defaultdict(list)
        for model in models:
            for run in model.runs:
                for temp in run.templates:
                    if temp.db_type:
                        db_threads[temp.db_type].append(temp)

        for model in models:
            scraper = workers.ScrapeWorker(model, store_q=self.store_q)
            self.scrapers[scraper.name] = scraper

        for thread, templates in db_threads.items():
            # TODO start the right database threads
            store_thread = databases._threads[thread](in_q=self.store_q)
            store_thread.start()
