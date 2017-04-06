from multiprocessing import Process, Queue, JoinableQueue, Lock, Value
from ctypes import c_int
import os


class ScrapeWorker(Process):
    def __init__(self, model, store_q=JoinableQueue()):
        super(ScrapeWorker, self).__init__()
        '''
        self.name = name
        self.domain = domain
        self.runs = runs
        self.time_out = time_out
        self.num_getters = num_getters
        self.session = session
        self.daemon = daemon
        '''

        self.source_q = JoinableQueue()
        self.store_q = store_q
        self.seen = set()
        self.forward_q = Queue()
        self.workers = []
        self.next_sources = set()
        self.to_forward = []
        self.parser = None
        self.lock = Lock()
        self.no_objects = False
        self.to_parse = Value(c_int)
        self.parsed = Value(c_int)
        self.total_sources = 0

        for attr in model.__dict__.keys():
            setattr(self, attr, getattr(model, attr))

    def run(self):
        # create the threads needed to scrape
        i = 0
        while self.runs:
            run = self.runs.pop(0)
            print('running run:', i)
            i += 1

            # Check if the run has a parser, if not, reuse the one from the
            # last run.
            if run.active:
                self.spawn_parser(run)
                self.spawn_workforce(run)
                self.add_sources(run)

                self.to_forward = [url for url in
                                   self.yield_from_process(self.forward_q,
                                                           self.parser)]
                # self.parser.join()
                print('parser_joined')
                with self.parser.to_parse.get_lock():
                    self.parser.to_parse.value = 0
                print('Unparsed ', self.source_q.qsize())
                print('forwarded', len(self.parser.forwarded))

                print('run', i-1, 'stopped')

                if run.repeat:
                    self.runs.append(run)
                    print('Repeating run', i-1)

            # Add Getters from the forward_list and empty it.
            with self.to_parse.get_lock():
                self.to_parse.value += self.forward_q.qsize()
            while not self.forward_q.empty():
                self.source_q.put(self.forward_q.get())

    def spawn_parser(self, run):
        if run.parser:
            self.parser = run.parser(parent=self, templates=run.templates,
                                     parsed=self.parsed)
            self.parser.start()

            print('parser started')
        elif not self.parser and not run.parser:
            raise Exception('No parser was specified')
        else:
            parse_class = self.parser.__class__
            print(parse_class)
            self.parser.in_q.put(None)
            self.parser.in_q.join()
            self.parser = parse_class(parent=self, templates=run.templates)
            self.parser.start()

    def spawn_workforce(self, run):
        # check if run reuses the current source workforce
        if run.n_workers and run.n_workers != self.num_getters:
            n_workers = run.n_workers
        else:
            n_workers = self.num_getters
        if not self.workers:
            for i in range(n_workers):
                worker = run.source_worker(parent=self, id=i,
                                           out_q=self.parser.in_q,
                                           time_out=self.time_out)
                worker.start()
                self.workers.append(worker)
        else:
            for worker in self.workers:
                worker.out_q = self.parser.in_q

    def add_sources(self, run):
        print('adding', self.forward_q.qsize(), 'from forward queue')
        # Add getters from Run
        with self.to_parse.get_lock():
            self.to_parse.value += len(self.to_forward)

        for source in self.to_forward:
            self.source_q.put(source)

        for source in run.sources:
            if source.active:
                self.source_q.put(source)
                with self.to_parse.get_lock():
                    self.to_parse.value += 1
        print('going to parse', self.parser.to_parse)

    def add_source(self, source):
        self.source_q.put(source)

    def yield_from_process(self, q, p):
        while p.is_alive():
            p.join(timeout=1)
            while True:
                try:
                    yield q.get(block=False)
                except:
                    self.show_progress()
                    break

    def show_progress(self):
        # os.system('clear')
        info = '''
        Sources to get:   {}
        Sources to parse: {}
        Sources parsed:   {}
        Parser has not crashed: {}
        '''
        print(info.format(self.source_q.qsize(),
                        self.to_parse.value,
                        self.parsed.value,
                        self.parser.is_alive()))
