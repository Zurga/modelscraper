from collections import defaultdict, ChainMap
from copy import copy
from datetime import datetime
from itertools import zip_longest, chain
from functools import partial
from threading import BoundedSemaphore
from queue import Empty, Queue
from threading import Lock

import inspect
import logging
import pprint
import re
import types

from pybloom_live import ScalableBloomFilter

from .parsers import HTMLParser
from .helpers import str_as_tuple, wrap_list, get_name
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
        This is the Source into which new urls will be submitted from either an
        Attr on from a Template. In the case of an Attr, each value found by the
        func specified will be used as an URL. Every other Attr in the Template is
        available when the URL is passed to the Source. This also means that certain
        values can be inserted in the keyword arguments which are available for the
        different Sources.


    kws : dict or list of dict, optional
        These are the keywords that will be passed to the 'func'
        attribute. If multiple funcs are given, the
    name : string, optional
        Used to register the Attr in the Template or the Template in the  Scraper.
        If none is provided, the variable name given in the model definition
        will be used.
    """

    def __init__(self, name='', emits=None):
        if not name:
            name = get_name(self)
            assert name, "Please specify a name or assign to a variable."
        self.name = name
        '''
        '''
        self.emits = emits
        '''
        An instance of a Source which will be used to get the new data.
        Which data will be passed in the queue of the source depends on
        the class it is used in, see the respective classes for their
        respective uses.
        '''

    def __call__(self, **kwargs):
        parameters = inspect.signature(self.__init__).parameters
        own_kwargs = [name for name in parameters
                      if name not in ('args', 'kwargs')]
        kwargs = {**{k:self.__dict__[k] for k in own_kwargs}, #noqa
                  **kwargs}

        return self.__class__(**kwargs)  # noqa


class Source(object):
    '''
    Attributes
    ==========
    name : string, optional
        Used for logging purposes.

    attrs : list of dict, dict, optional
        The keys and values in the attrs will be passed to each object created
        while parsing the data which came from this source. If a single dict is
        passed, all the objects will have the same keys and values applied.

        If a list is passed with the same length as the urls, the urls and attrs
        will be zipped. I.E. each object from a specific URL will have specific
        attrs.

    url_template : string, optional
        A string which can be formatted using the "str.format" notation. Whatever
        is used as URL will be placed inside the "{}".
        I.E. url_template = 'https://duckduckgo.com/q={}'

    urls : list of strings, optional
        A list of URLs from which data is to be retrieved.

    test_urls : list of strings, optional
        A list of URLs which will be used when the ":Scraper.dummy:" parameter
        is set to True.

    n_workers : int, optional
        The amount of workers (or Threads) used by the workers of the Source

    compression : string, optional
        The compression type used for the data retrieved from each URL. At the
        moment only Zip and Gzip are supported

    kwargs_format : dict, optional
        A mapping
    '''
    kwargs = []
    def __init__(self, name='', attrs=[], url_template='{}', url_regex='',
                 urls=[], func='', test_urls=[], n_workers=1, compression='',
                 kwargs_format={}, duplicate=False, debug=False):
        self.attrs = attrs
        self.compression = compression
        self.duplicate = duplicate
        self.func = func
        self.kwargs_format = kwargs_format
        self.n_workers = n_workers
        self.test_urls = str_as_tuple(test_urls)
        self.url_template = url_template
        self.urls = urls
        self.debug = debug

        # Compile the url_regex
        self.url_regex = re.compile(url_regex).search if url_regex else False

        if not name:
            name = get_name(self)
        self.name = name

        self._backup_sources = None
        self._semaphore = BoundedSemaphore(self.n_workers)
        self.in_q = Queue()
        self.lock = Lock()
        self.out_q = Queue()
        self.seen = ScalableBloomFilter()
        self.to_parse = 0
        self.upstream_sources = []
        self.url_amount = int((self.n_workers / 2) + 10)
        self.url_attrs = defaultdict(dict)
        self.models = []

    @property
    def semaphore(self):
        return self._semaphore

    @semaphore.setter
    def semaphore(self, semaphore):
        if semaphore._value == self.n_workers:
            self._semaphore = semaphore
        else:
            self._semaphore = BoundedSemaphore(self.n_workers)

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

    def start(self):
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
            if self.debug:
                print(data)
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
        if self.urls:
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

                if self.attrs:
                    if type(self.attrs) is list:
                        attrs = self.attrs.pop()
                    elif type(self.attrs) is dict:
                        attrs = self.attrs
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
        url = self.url_template.format(url)
        if url not in self.seen or self.duplicate:
            if self.url_regex and not self.url_regex(url):
                return False
            kwargs = self.get_kwargs(objct)
            self.url_attrs[url] = attrs
            self.in_q.put((url, kwargs))
            self.to_parse += 1
            self.add_to_seen(url)

    def get_kwargs(self, objct=None):
        kwargs = {}
        for key in self.kwargs:
            kwarg = getattr(self, key)
            if kwarg:
                # If the kwargs are in a list or generator, we get the next
                # value.
                if type(kwarg) is list:
                    value = kwarg.pop(0)
                elif type(value) is types.GeneratorType:
                    try:
                        value = next(value)
                    except StopIteration:
                        continue

                # Format the value for the keyword argument based on an object
                # that was passed.
                if objct and key in self.kwargs_format and type(value) is str:
                    value = value.format(**{k: objct[k] for k in
                                            self.kwargs_format[key]})

                kwargs[key] = value
        return kwargs

    def use_test_urls(self):
        if type(self.urls) != types.GeneratorType:
            self._backup_sources = copy(self.urls)
        else:
            self._backup_sources = self.urls
        self.urls = self.test_urls if hasattr(self, 'test_urls') else self.urls

    def restore_urls(self):
        if self._backup_sources:
            self.urls = self._backup_sources

    def get_attr_names(self, caller=None):
        if self.attrs:
            attrs_copy = copy(self.attrs)
            if type(attrs_copy) in (list, types.GeneratorType):
                for attr in attrs_copy:
                    for name in attr.keys():
                        yield name
            elif type(attrs_copy) == dict:
                for name in attrs_copy.keys():
                    yield name

    def register_model(self, model):
        if model not in self.models:
            self.models.append(model)


class Attr(BaseComponent):
    '''
    An Attr is used to hold a value for a model.
    This value is created by selecting data from the source using the selector,
    after which the "func" is called on the selected data.

    func : method or list of methods, optional
        One or multiple methods provided by a Parser. If a list is given, the data
        from one method is passed onto another. The methods can be from different
        parsers, the data will be converted by the parser.
        For example, a combination of these two methods will allow for the
        selection of JSON which is embedded in HTML like this:
        <span>{"test": "value"}</span>

        htmlp = HTMLParser()
        jsonp = JSONParser()
        nested_json = Attr(name='nested', func=[htmlp.text(selector='span'),
                                                jsonp.text(selector='test')])


    transfers : bool, default False
        This determines whether the Attr will be copied as a name: value pair to the
        source which another Attr might be emitting into.
        Consider the following example where an image url scraped with the category
        attribute from the same model by setting the 'transfers' parameter to True on         the category attribute:

        htmlp = HTMLParser()
        image_list_source = WebSource()
        image_source = WebSource()

        image_url = Attr(func=htmlp.attr(selector='img', attr='src'),
                         emits=image_source)
        category = Attr(func=htmlp.text(selector='span.category'),
                        transfers=True)

        model = Model(source=image_list_source, attrs=[domain, url])

        The objects that are generated from the data in the image_source will
        now also have a category attribute set to whatever value was gotten from
        the image_list_source.
    '''
    def __init__(self, name='', func=None, value=None, attr_condition={},
                 source_condition={}, from_source=False, type=None,
                 transfers=False, raw_data=False, *args, **kwargs):
        super().__init__(name=name, *args, **kwargs)
        assert (from_source and not self.emits) or not from_source, \
            "If the attr is coming from a source, it cannot emit into another source"
        self.func = wrap_list(func)
        self.value = wrap_list(value)
        self.attr_condition = attr_condition
        self.source_condition = source_condition
        self.type = type
        self.from_source = from_source
        self.transfers = transfers
        self.raw_data = raw_data

    def __getstate__(self):
        state = {}
        state['name'] = self.name
        state['type'] = self.type
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

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


class Model(BaseComponent):
    def __init__(self, attrs=[], dated=False, database=[], preparser=None,
                 required=False, selector=None, source=None, table='',
                 kws={}, overwrite=True, definition=False, debug=False, *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs = attr_dict(attrs)
        self.dated = dated
        self.database = wrap_list(database)
        self.debug = debug
        self.kws = kws
        self.preparser = preparser
        self.required = required
        self.selector = wrap_list(selector)
        self.source = wrap_list(source)
        self.table = table
        self.overwrite = overwrite
        self.definition = definition

        # Get the urls of the objects that have already been parsed to avoid
        # overwriting them.
        if dated:
            self.attrs['_date'] = Attr(name='_date')

        if not definition:
            if not self.overwrite:
                for db in self.database:
                    for obj in db.read(self):
                        self.source.add_to_seen(obj.get('url'))

            self.emit_attrs = [attr for attr in self.attrs
                               if attr.emits]

            if not self.emits:
                self.transfers = [attr.name for attr in self.attrs
                                  if attr.transfers]
            else:
                self.transfers = self.attrs.keys()

            self.func_attrs = [attr for attr in self.attrs
                               if attr.func]
            self.value_attrs = [attr for attr in self.attrs
                                if attr.value]

            if 'url' not in self.attrs:
                self.attrs['url'] = Attr(name='url')


    def __call__(self, definition=False, attrs=[], *args, **kwargs):
        # Check if the same attrs are being used as in the definition
        if self.definition:
            for attr in attrs:
                if attr.name not in self.attrs:
                    print('Missing', attr.name, 'in the implementation')
                    raise Exception('You must use the same attrs when ' + \
                                    'implementing a definition')
        return super().__call__(definition=definition, attrs=attrs, *args,
                                **kwargs)

    def __getstate__(self):
        pickled = ['attrs', 'table', 'kws', 'name', ]
        dic = {p: self.__dict__[p] for p in pickled}
        return dic

    def __setstate__(self, state):
        self.__dict__.update(state)

    def validate(self):
        # Validate the functions of the attrs
        for attr in self.attrs:
            for database in self.database:
                database.check_forbidden_chars(attr.name)
        if not self.table:
            for database in self.database:
                if not database.table:
                    raise Exception(str(self.name) +
                                    ' model needs a table to be set')

    def attrs_to_dict(self):
        return {a.name: a.value for a in self.attrs}

    def gen_source(self, objects):
        for attr in self.emit_attrs:
            # If a mapping has been passed, we pass the previous url on to the next
            # source.
            if isinstance(attr.emits, dict):
                for objct in objects:
                    attrs = {'_url': objct['_url']}
                    for value in objct[attr.name]:
                        if value:
                            source = attr.emits.get(value)
                            if source:
                                source.add_source(objct['_url'], attrs, objct)
            else:
                for objct in objects:
                    if attr._evaluate_condition(objct):
                        for url in objct[attr.name]:
                            if url:
                                attrs = {key: objct[key] for key in self.transfers}
                                attrs['_url'] = objct['_url']
                                attr.emits.add_source(url, attrs, objct)

        if self.emits:
            for objct in objects:
                urls = objct.get('url', False)
                if urls:
                    for url in urls:
                        self.emits.add_source(url, objct, objct)
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
                if attr.raw_data:
                    value = (raw_data,)
                else:
                    value = [data]
                #try:
                for func in attr.func:
                    value = [result for v in value for result in func(url, v)]
                obj[attr.name] = value
                #except Exception as E:
                #    print(self.name, E)
                #    print(attr.name, attr.func)

            for attr in self.value_attrs:
                obj[attr.name] = attr.value

            if not 'url' in obj:
                obj['url'] = [obj['_url']]

            urls.extend(obj.get('url', []))
            if self.dated:
                obj['_date'] = str(datetime.now())
            objects.append(obj)
        if self.debug:
            print(self.name, url, 'parsed:')
            pp.pprint(objects)
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
    def __init__(self, name='', models=[], num_sources=1, awaiting=False,
                 schedule='', logfile='', dummy=False, recurring=[]):
        super().__init__()
        self.name = name
        self.models = models
        self.num_sources = num_sources
        self.awaiting = awaiting
        self.schedule = schedule
        self.sources = set()
        self.recurring = recurring
        self._dummy = dummy

        # Set up the logging
        if logfile:
            logging.basicConfig(filename=logfile, level=logging.WARNING)
        else:
            logging.basicConfig(level=logging.WARNING)
        self.databases, parsers = set(), set()

        # Populate lists of the databases used, the parsers and the sources
        for model in self.models:
            model.validate()
            for source in model.source:
                source.register_model(model)
                if model.emits:
                        model.emits.register_upstream_source(source)
                self.sources.add(source)

            # Register the upstream sources for each source that expects something.
            for attr in model.emit_attrs:
                for source in model.source:
                    attr.emits.register_upstream_source(source)

            for db in model.database:
                self.databases.add(db)

        # Restrict the amount of source workers working at the same time.
        self.semaphore = BoundedSemaphore(self.num_sources)
        for source in self.sources:
            source.semaphore = self.semaphore

        self.validate()

    def validate(self):
        """
        A valid model contains Templates where each Template parses at least one source,
        if a Template or an Attr emits a source, this source is also used in at least
        one Template.
        """
        unused_source = "The attr {} emits a source which is not used by any Template"
        for model in self.models:
            for attr in model.emit_attrs:
                assert attr.emits in self.sources,\
                    unused_source.format(attr.name)

        upstream_attrs = defaultdict(set)

        for model in self.models:
            sources = []
            sources.extend(model.source)
            while sources:
                source = sources.pop()
                for name in source.get_attr_names():
                    upstream_attrs[model].add(name)
                for upstream_model in source.models:
                    for name in upstream_model.transfers:
                        upstream_attrs[model].add(name)
                    sources.extend(source.upstream_sources)

        for model, attrs in upstream_attrs.items():
            for attr in attrs:
                if attr not in model.attrs:
                    print('This attr should be added to the model',
                          model.name, attr)

    @property
    def dummy(self):
        return self._dummy

    @dummy.setter
    def dummy(self, value):
        if value:
            self._dummy = value
            for source in self.sources:
                source.use_test_urls()
                # Backup the urls of the source in a different attribute
        else:
            for source in self.sources:
                source.restore_urls()

    def start(self):
        '''
        Processes the urls in the sources provided by the model.
        Every iteration processes the data retrieved from one url for each Source.
        '''
        self.start_databases()
        self.start_sources()
        while self.sources:
            empty = []
            for source in self.sources:
                res = source.get_source()
                if res:
                    url, attrs, data = res
                    for model in source.models:
                        objects, urls = model.parse(url, attrs, data)
                        if objects:
                            print('Parsed', model.name, source.name, url, len(objects))
                            model.store_objects(objects, urls)
                            model.gen_source(objects)
                            if self.dummy:
                                pp.pprint(objects)
                        else:
                            print('no objects', model.name, url)
                elif res == False:
                    logging.log(logging.INFO, 'stopping' + str(source.name))
                    empty.append(source)
                else:
                    continue
            for source in empty:
                self.sources.discard(source)
        self.kill_databases()

    def start_sources(self):
        for source in self.sources:
            source.start()

    def start_databases(self):
        for db in self.databases:
            db.start()

    def kill_databases(self):
        for db in self.databases:
            db.stop()

    def __repr__(self):
        repr_string = self.name + ':\n'
        for model in self.models:
            repr_string += '\t{}\n'.format(model.name)
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
