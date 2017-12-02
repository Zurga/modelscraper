from . import workers
from multiprocessing import Queue
from collections import defaultdict
import sys
import cProfile


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

        # TODO fix this part
        """
        for scraper in self.scrapers.values():
            while scraper.awaiting and scraper.source_q.empty():
                url = input('url: ')
                scraper.add_source(url)
        """
        # TODO fix that the seen urls go to the databases.
        print('joined')

        self.store_q.put(None)

    def add_scraper(self, models, dummy=False):
        if type(models) != list:
            models = [models]

        for model in models:
            print('dummy', dummy)
            scraper = workers.ScrapeWorker(model, dummy=dummy)
            self.scrapers[scraper.name] = scraper

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
        for scraper, percent, phase in progress:
            bar = ('=' * int(percent * 20)).ljust(20)
            percent = int(percent * 100)
            sys.stdout.write("%s %s [%s] %s%%\n" % (scraper, phase,
                                                    bar, percent))
            sys.stdout.flush()
