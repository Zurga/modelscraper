from collections import defaultdict, ChainMap
from datetime import datetime
from itertools import zip_longest, chain
from functools import partial
from threading import BoundedSemaphore
from multiprocessing import Process, JoinableQueue
from queue import Empty
from threading import Lock

import logging
import pprint
import inspect
import types

from pybloom_live import ScalableBloomFilter

from .parsers import HTMLParser
from .helpers import str_as_tuple, wrap_list
from . import databases


pp = pprint.PrettyPrinter(indent=4)
logger =  logging.getLogger(__name__)


class BaseComponent(object):
    """
    A class that provides common functions for other components as well
    as common attributes.

    Attributes
    ==========
    emits : Source, optional
    kws : dict or list of dict, optional
        These are the keywords that will be passed to the 'func'
        attribute. If multiple funcs are given, the
    name : string, optional
        The name given used in by the parser for this Template or attribute.
    selector : Test
    """

    def __init__(self, emits=None, kws={}, name=None, selector=None):
        self.emits = emits
        '''
        An instance of a Source which will be used to get the new data.
        Which data will be passed in the queue of the source depends on
        the class it is used in, see the respective classes for their
        respective uses.
        '''
        self.name = name
        '''
        The name which will be used to print and register the object in the
        Template or Scraper
        '''
        self.selector = wrap_list(selector)
        '''
        A selector which will be used to gather the information to which the
        template is applied.
        '''
        self.kws = wrap_list(kws)

    def _replicate(self, **kwargs):
        return self.__class__(**kwargs)

    def __call__(self, **kwargs):
        parameters = inspect.signature(self.__init__).parameters
        own_kwargs = [name for name in parameters
                      if name not in ('args', 'kwargs')]
        kwargs = {**{k:self.__dict__[k] for k in own_kwargs}, #noqa
                  **kwargs}

        return self.__class__(**kwargs)  # noqa


class Source(object):
    kwargs = []
    def __init__(self, name='', kws={}, attrs=[], url_template='{}',
                 urls=[], func='', test_urls=[], n_workers=1, compression='',
                 kwargs_format={}, duplicate=False, repeat=False,
                 wait=False):
        self.attrs = attrs
        self.compression = compression
        self.duplicate = duplicate
        self.func = func
        self.kwargs_format = kwargs_format
        self.kws = kws
        self.n_workers = n_workers
        self.name = name
        self.repeat = repeat
        self.url_template = url_template
        self.urls = urls

        self._backup_sources = None
        self._semaphore = BoundedSemaphore(self.n_workers)
        self.in_q = JoinableQueue()
        self.lock = Lock()
        self.out_q = JoinableQueue()
        self.seen = ScalableBloomFilter()
        self.test_urls = str_as_tuple(test_urls)
        self.to_parse = 0
        self.upstream_sources = []
        self.url_amount = int((self.n_workers / 2) + 10)
        self.url_attrs = defaultdict(dict)
        self.wait = wait

        if not self.urls or wait:
            self.received = False
        else:
            self.received = True

    @property
    def semaphore(self):
        return self._semaphore

    @semaphore.setter
    def semaphore(self, semaphore):
        if semaphore._value == self.n_workers:
            self._semaphore = semaphore
        else:
            self._semaphore = BoundedSemaphore(self.n_workers)
        self.initialize_workers()

    def register_upstream_source(self, source):
        if self != source and source not in self.upstream_sources:
            self.upstream_sources.append(source)

    def remove_upstream_source(self, source):
        if source in self.upstream_sources:
            self.upstream_sources.pop(self.upstream_source.index(source))

    def is_upstream_alive(self):
        return any(source.is_alive() for source in self.upstream_sources)

    def is_alive(self):
        return any(worker.is_alive() for worker in self.workers)

    def retrieving(self):
        return any(w.retrieving for w in self.workers)

    def initialize_workers(self):
        self.workers = [
            self.source_worker(parent=self, id=1, in_q=self.in_q,
                               out_q=self.out_q, semaphore=self._semaphore,
                               lock=self.lock)
            for _ in range(self.n_workers)]

        for worker in self.workers:
            worker.start()

    @classmethod
    def from_db(cls, database, table='', url='url', query={}, **kwargs):
        for obj in database.read(table=table, query=query):
            attr = t.attrs.pop(url, [])
            if type(attr.value) is not list:
                values = [attr.value]
            else:
                values = attr.value
            for v in values:
                yield cls(url=v, **kwargs)

    def get_source(self):
        assert self.workers, "No workers have been started, call \
            'initialize_workers'"
        self.consume()

        try:
            url, data = self.out_q.get(timeout=1)
            attrs = self.url_attrs[url]
            self.out_q.task_done()
            self.to_parse -= 1
            if not data:
                logging.log(logging.WARNING, str(url) + 'no data was returned')
                return None
            return url, attrs, data
        except Empty:
            if self._should_terminate():
                self.stop()
                return False

    def _should_terminate(self):
        if not self.upstream_sources and not self.to_parse and not self.retrieving():
            return True
        elif self.upstream_sources and not self.is_upstream_alive() and not \
            self.to_parse and not self.retrieving():
            return True
        return False

    def stop(self):
        for worker in self.workers:
            self.in_q.put(None)
        for worker in self.workers:
            worker.join()
        print('Source.stop stopped', self.name)

    def consume(self):
        if self.urls and not self.wait:
            for _ in range(self.url_amount):
                if type(self.urls) is list:
                    try:
                        url = self.urls.pop()
                    except IndexError:
                        self.urls = False
                        break
                elif isinstance(self.urls, types.GeneratorType):
                    try:
                        url = next(self.urls)
                    except StopIteration:
                        self.urls = False
                        break

                if self.attrs and type(self.attrs) is list:
                    attrs = self.attrs.pop()
                else:
                    attrs = {}

                self.url_attrs[url] = attrs
                kwargs = self.get_kwargs()

                url = self.url_template.format(url)
                self.in_q.put((url, kwargs))
                self.to_parse += 1
                self.add_to_seen(url)

    def add_to_seen(self, url):
        self.seen.add(url)

    def add_source(self, url, attrs, objct={}):
        self.received = True
        self.wait = False
        url = self.url_template.format(url)
        if (url not in self.seen or self.repeat) or self.duplicate:
            kwargs = self.get_kwargs(objct)
            self.url_attrs[url] = attrs
            self.in_q.put((url, kwargs))
            self.to_parse += 1
            self.add_to_seen(url)

    def get_kwargs(self, objct=None):
        kwargs = {}
        for key in self.kwargs:
            value = getattr(self, key)
            if value:
                # If the kwargs are in a list or generator, we get the next
                # value.
                if type(value) is list:
                    value = value.pop(0)
                elif type(value) is types.GeneratorType:
                    try:
                        value = next(value)
                    except StopIteration:
                        continue

                # Format the value for the keyword argument based on an object
                # that was passed.
                if objct and key in self.kwargs_format and type(value) is str:
                    value = value.format(**{k:objct[k] for k in
                                            self.kwargs_format[key]})

                kwargs[key] = value
        return kwargs

    def use_test_urls(self):
        if type(self.urls) != types.GeneratorType:
            self._backup_sources = copy(self.urls)
        else:
            self._backup_sources = self.urls
        self.urls = self.test_urls if hasattr(self, 'test_urls') else []

    def restore_urls(self):
        if self._backup_sources:
            self.urls = self._backup_sources


class Attr(BaseComponent):
    '''
    An Attr is used to hold a value for a template.
    This value is created by selecting data from the source using the selector,
    after which the "func" is called on the selected data.
    '''
    def __init__(self, func=None, value=None, attr_condition={},
                 source_condition={}, type=None, arity=1, from_source=False,
                 transfers=False, stores=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.func = wrap_list(func)
        self.value = wrap_list(value)
        self.attr_condition = attr_condition
        self.source_condition = source_condition
        self.type = type
        self.arity = arity
        self.from_source = from_source
        self.transfers = transfers
        self.stores = True

        # Ensure that the kws are encapsulated in a list with the same length
        # as the funcs.
        '''
        if self.func:
            self.kws = wrap_list(self.kws)
            difference = len(self.func) - len(self.kws)
            if difference:
                self.kws = [*self.kws, *[{} for _ in range(difference)]]
        '''

    def __call__(self, **kwargs):
        new_kws = kwargs.get('kws', {})
        if new_kws:
            new_kws = wrap_list(new_kws)
            kwargs['kws'] = [{**old, **new} for new, old in
                            zip_longest(new_kws, self.kws, fillvalue={})]
        # TODO maybe a ChainMap here?
        return self.__class__(**{**self.__dict__, **kwargs})  # noqa

    def __getstate__(self):
        state = {}
        state['name'] = self.name
        state['type'] = self.type
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def set_name(self):
        for name, var in globals().items():
            if self == var:
                print(name, var)
                self.name = name

    def _evaluate_condition(self, objct):
        # TODO fix this ugly bit of code
        if self.source_condition:
            expression = ''

            for operator, attrs in self.source_condition.items():
                expression += (' '+operator+' ').join(
                    [str(value) + c for name, c in attrs.items()
                        for value in objct[name]])
            if expression:
                return eval(expression, {}, {})
            else:
                return False
        return True


class AttrDict(dict):
    def __iter__(self):
        for val in self.values():
            yield val


def attr_dict(attrs):
    if type(attrs) == AttrDict:
        return attrs
    attrs_dict = AttrDict()
    for attr_item in attrs:
        attrs_dict[attr_item.name] = attr_item
    return attrs_dict


class Template(BaseComponent):
    def __init__(self, attrs=[], dated=False, database=[], func='create',
                 parser=HTMLParser, preparser=None, required=False,
                 source=None, table='', url='', overwrite=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs = attr_dict(attrs)
        self.dated = dated
        self.database = wrap_list(database)
        self.func = func
        self.parser = wrap_list(parser)
        self.preparser = preparser
        self.required = required
        self.source = wrap_list(source)
        self.table = table
        self.url = url
        self.overwrite = overwrite

        # Get the urls of the objects that have already been parsed to avoid
        # overwriting them.
        if not self.overwrite:
            for db in self.database:
                for obj in db.read(self):
                    self.source.add_to_seen(obj.get('url'))

        if self.url:
            self.attrs['url'] = Attr(name='url', value=self.url)

        self.emit_attrs = [attr for attr in self.attrs
                           if attr.emits]

        # Register the upstream sources for each source that expects something.
        for attr in self.emit_attrs:
            for source in self.source:
                attr.emits.register_upstream_source(source)

        if self.emits:
            for source in self.source:
                self.emits.register_upstream_source(source)

        self.transfers = [attr.name for attr in self.attrs
                          if attr.transfers]
        self.func_attrs = [attr for attr in self.attrs
                           if attr.func]
        self.value_attrs = [attr for attr in self.attrs
                            if attr.value]

    def validate(self):
        # Validate the functions of the attrs
        for parser in self.parser:
            for attr in self.attrs:
                for database in self.database:
                    database.check_forbidden_chars(attr.name)
        if not self.table:
            for database in self.database:
                if not database.table:
                    raise Exception(str(self.name) +
                                    ' template needs a table to be set')

    def attrs_to_dict(self):
        return {a.name: a.value for a in self.attrs}

    def __getstate__(self):
        pickled = ['attrs', 'table', 'func', 'kws',
                   'name', 'url', ]
        dic = {p: self.__dict__[p] for p in pickled}
        return dic

    def __setstate__(self, state):
        self.__dict__.update(state)

    def gen_source(self, objects):
        for attr in self.emit_attrs:
            # If a mapping has been passed, we pass the previous url on to the next
            # source.
            if isinstance(attr.emits, dict):
                for objct in objects:
                    attrs = {'_url': objct['_url']}
                    for value in objct[attr.name]:
                        source = attr.emits.get(value)
                        if source:
                            source.add_source(objct['_url'], attrs, objct)
            else:
                for objct in objects:
                    if attr._evaluate_condition(objct):
                        for url in objct[attr.name]:
                            attrs = {key: objct[key] for key in self.transfers}
                            attrs['_url'] = objct['_url']
                            attr.emits.add_source(url, attrs, objct)

        if self.emits:
            for objct in objects:
                urls = objct.get('url', False)
                if urls:
                    for url in urls:
                        self.emits.add_source(url, {}, objct)
                else:
                    warning = 'No url is specified for object {}. Cannot emit source.'
                    logging.warning(warning.format(self.name))
        return True

    def attrs_from_dict(self, attrs):
        self.attrs = attr_dict((Attr(name=name, value=value) for
                      name, value in attrs.items()))

    def parse(self, url, attrs, raw_data, verbose=False):
        objects, urls = [], []

        if self.selector:
            extracted = raw_data
            for sel in self.selector:
                extracted = sel(url, extracted)
        else:
            extracted = (raw_data,)

        for data in extracted:
            obj = {'_url': url, **attrs}

            no_value = 0
            for attr in self.func_attrs:
                value = data
                try:
                    for func in attr.func:
                        value = func(url, value)
                    obj[attr.name] = list(value)
                except Exception as E:
                    print(attr.name, attr.func)

            for attr in self.value_attrs:
                obj[attr.name] = attr.value

            urls.extend(obj.get('url', []))
            if self.dated:
                obj['_date'] = str(datetime.now())
            objects.append(obj)

        return objects, urls

    def store_objects(self, objects, urls):
        for db in self.database:
            db.store(self, objects, urls)

    # TODO fix to new database spec
    def query(self, query={}):
        db_type = getattr(databases, db_type)
        if isinstance(db_type, type):
            db_type = db_type()
        yield from db_type().read(self,query=query)

    def all(self):
        yield from self.query()


class Scraper(object):
    def __init__(self, name='', templates=[], num_sources=1, awaiting=False,
                 schedule='', logfile='', dummy=False, recurring=[], **kwargs):
        super().__init__()
        self.name = name
        self.templates = templates
        self.num_sources = num_sources
        self.awaiting = awaiting
        self.schedule = schedule
        self.sources = {}
        self.recurring = recurring
        self._dummy = dummy

        # Set up the logging
        if logfile:
            logging.basicConfig(filename=logfile, level=logging.WARNING)
        else:
            logging.basicConfig(level=logging.WARNING)
        self.databases, parsers = set(), set()
        self.sources_templates = defaultdict(list)

        # Populate lists of the databases used, the parsers and the sources
        for template in self.templates:
            template.validate()
            for source in template.source:
                self.sources_templates[source].append(template)
            for db in template.database:
                self.databases.add(db)

        # Restrict the amount of source workers working at the same time.
        self.semaphore = BoundedSemaphore(self.num_sources)
        for source in self.sources_templates:
            source.semaphore = self.semaphore

        self.validate()

    def validate(self):
        """
        A valid model contains Templates where each Template parses at least one source,
        if a Template or an Attr emits a source, this source is also used in at least
        one Template.
        """
        unused_source = "The attr {} emits a source which is not used by any Template"
        for template in self.templates:
            for attr in template.emit_attrs:
                assert attr.emits in self.sources_templates,\
                    unused_source.format(attr.name)

    @property
    def dummy(self):
        return self._dummy

    @dummy.setter
    def dummy(self, value):
        if value:
            self._dummy = value
            for source in self.sources_templates:
                source.use_test_urls()
                # Backup the urls of the source in a different attribute
        else:
            for source in self.sources_templates:
                source.restore_urls()

    def start(self):
        '''
        Processes the urls in the sources provided by the model.
        Every iteration processes the data retrieved from one url for each Source.
        '''
        self.start_databases()
        while self.sources_templates:
            empty = []
            for source, templates in self.sources_templates.items():
                res = source.get_source()
                if res:
                    url, attrs, data = res
                    for template in templates:
                        objects, urls = template.parse(url, attrs, data)
                        #pp.pprint(objects)
                        if objects:
                            print(source.name, len(objects))
                            template.store_objects(objects, urls)
                            template.gen_source(objects)
                        else:
                            print('no objects', url)
                elif res == False:
                    logging.log(logging.INFO, 'stopping' + source.name)
                    empty.append(source)
                else:
                    continue
            for source in empty:
                source = self.sources_templates.pop(source)
                del source
        self.kill_databases()

    def start_databases(self):
        for db in self.databases:
            db.start()

    def kill_databases(self):
        for db in self.databases:
            db.stop()

    def get_template(self, template):
        if type(template) is Template:
            key = template.name
        elif type(template) is str:
            key = template
        for template in self.templates:
            if template.name == key:
                return template

    def __repr__(self):
        repr_string = self.name + ':\n'
        for template in self.templates:
            repr_string += '\t{}\n'.format(template.name)
        return repr_string

    # TODO fix this method
    def show_progress(self):
        # os.system('clear')
        info = '''
        Domain              {}
        Sources to get:     {}
        Sources to parse:   {}
        Sources parsed:     {} {}%
        Average get time:   {}s
        Average parse time: {}s
        '''
        get_average = sum(w.mean for w in self.workers) / len(self.workers)
        print(info.format(self.name,
                          self.phase,
                          self.source_q.qsize(),
                          self.to_parse,
                          self.parsed, (self.parsed / self.to_parse) * 100,
                          round(get_average, 3),
                          round(self.total_time / self.parsed, 3)
                          ))
