from . import workers
from multiprocessing import Queue
from . import databases
from collections import defaultdict
import sys


class Dispatcher:
    def __init__(self):
        self.scrapers = {}

        self.store_q = Queue()
        self.results = []
        self.store_threads = []

    def run(self):
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

        # TODO fix that the seen urls go to the databases.
        print('joined')

        self.store_q.put(None)

    def add_scraper(self, models):
        if type(models) != list:
            models = [models]

        db_threads = defaultdict(list)

        for model in models:
            for run in model.runs:
                for template in run.templates:
                    if template.db_type:
                        db_threads[template.db_type].append(template)

                    self._check_functions(template, run)

        for model in models:
            scraper = workers.ScrapeWorker(model, store_q=self.store_q)
            self.scrapers[scraper.name] = scraper

        for thread, templates in db_threads.items():
            print('starting', thread)
            store_thread = databases._threads[thread](in_q=self.store_q)
            store_thread.start()

    def _check_functions(self, template, run):
        error_string = "One of these functions: {} is not implemented in {}."
        not_implemented = []

        for attr in template.attrs.values():
            for func in attr.func:
                if not getattr(run.parser, func, False):
                    not_implemented.append(func)

        if not_implemented:
            raise Exception(error_string.format(str(not_implemented),
                                                run.parser.__class__.__name__))

    def print_progress(progress):
        sys.stdout.write('\033[2J\033[H')  # clears the screen
        for scraper, percent, run in progress:
            bar = ('=' * int(percent * 20)).ljust(20)
            percent = int(percent * 100)
            sys.stdout.write("%s %s [%s] %s%%\n" % (scraper, run,
                                                    bar, percent))
            sys.stdout.flush()
