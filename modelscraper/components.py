from collections import defaultdict, ChainMap
from datetime import datetime
from itertools import zip_longest, chain
from functools import partial
from threading import BoundedSemaphore
from multiprocessing import Process
import logging
import pprint
import inspect

from .parsers import HTMLParser
from .helpers import str_as_tuple, wrap_list
from . import databases


pp = pprint.PrettyPrinter(indent=4)
logger =  logging.getLogger(__name__)


class BaseComponent(object):
    def __init__(self, emits=None, kws={}, name=None, selector=None):
        self.emits = emits
        self.kws = kws
        self.name = name
        self.selector = selector

    def _replicate(self, **kwargs):
        return self.__class__(**kwargs)

    def __call__(self, **kwargs):
        parameters = inspect.signature(self.__init__).parameters
        own_kwargs = [name for name in parameters
                      if name not in ('args', 'kwargs')]
        kwargs = {**{k:self.__dict__[k] for k in own_kwargs}, #noqa
                  **kwargs}

        return self.__class__(**kwargs)  # noqa


class Attr(BaseComponent):
    '''
    An Attr is used to hold a value for a template.
    This value is created by selecting data from the source using the selector,
    after which the "func" is called on the selected data.
    '''

    def __init__(self, func=None, value=None, attr_condition={},
                 source_condition={}, type=None, arity=1, from_source=False,
                 transfers=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.func = str_as_tuple(func)
        self.value = value
        self.attr_condition = attr_condition
        self.source_condition = source_condition
        self.type = type
        self.arity = arity
        self.from_source = from_source
        self.transfers = transfers

        # Ensure that the kws are encapsulated in a list with the same length
        # as the funcs.
        if self.func:
            self.kws = wrap_list(self.kws)
            difference = len(self.func) - len(self.kws)
            if difference:
                self.kws = [*self.kws, *[{} for _ in range(difference)]]

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
            print(name, var)
            if self == var:
                print(name, var)
                self.name = name

    def set_func(self, parser):
        self.func = [partial(getattr(parser, func), **kw)
                    if type(func) == str
                    else func
                    for func, kw in zip(self.func, self.kws)]

    def _format_source_kws(self, source):
        if source.add_value and source.copy_attrs:
            for keyword, attrs in self.add_value.items():
                values = {attr: self.attrs[attr].value[0] for attr in
                          str_as_tuple(attrs) if self.attrs[attr].value}
                self.kws[keyword].format(**values)

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
        self.transfers = [attr.name for attr in self.attrs
                          if attr.transfers]

    def validate(self):
        # Validate the functions of the attrs
        for parser in self.parser:
            for attr in (a for a in self.attrs if not a.from_source):
                for database in self.database:
                    database.check_forbidden_chars(attr.name)
                for func in attr.func:
                    if type(func) is str and not getattr(parser, func, False):
                        raise Exception(
                            '{} does not exist in {}'.format(
                                func, parser.__name__))

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
            for objct in objects:
                if attr._evaluate_condition(objct):
                    for url in objct[attr.name]:
                        attrs = {key: objct[key] for key in self.transfers}
                        attr.emits.add_source(url, attrs, objct)

        if self.emits:
            for objct in objects:
                urls = objct.get('url', False)
                if urls:
                    for url in urls:
                        print('adding', url, objct, objct)
                        self.emits.add_source(url, objct, objct)
                else:
                    warning = 'No url is specified for object {}. Cannot emit source.'
                    logging.warning(warning.format(self.name))
        return True

    def attrs_from_dict(self, attrs):
        self.attrs = attr_dict((Attr(name=name, value=value) for
                      name, value in attrs.items()))

    def prepare(self, parsers=[]):
        # Instantiate the parser if none was provided
        if not parsers:
            self.parser = [p() for p in self.parser]
        else:
            self.parser = [parsers[p] for p in self.parser]

        if self.selector:
            if len(self.parser) > 1:
                self.selector = [parser.get_selector(selector)
                                for parser, selector in
                                zip_longest(self.parser, self.selector)]
            else:
                self.selector = [self.parser[0].get_selector(self.selector)]

        # Set the functions of the attrs
        parser = self.parser[-1]
        forwarded = []
        for attr in self.attrs:
            if attr.from_source:
                forwarded.append(attr.name)
            else:
                attr.set_func(parser)
                if attr.selector:
                    attr.selector = parser.get_selector(attr.selector)

        for attr in forwarded:
            self.attrs.pop(attr)

    def parse(self, url, attrs, data, verbose=False):
        objects, urls = [], []
        if self.preparser:
            data = self.preparser(data)
        if len(self.parser) > 1:
            for parser, selector in zip(self.parser[:-1],
                                        self.selector[:-1]):
                data = parser.parse(url, data, self, selector=selector,
                                    gen_objects=False)

            parser = self.parser[-1]
        else:
            parser = self.parser[0]
        if self.selector:
            selector = self.selector[-1]
        else:
            selector = None

        count = 0
        # Create the actual objects
        for i, obj in enumerate(parser.parse(url, data, template=self,
                                             selector=selector)):
            count += i
            obj = {**obj, **attrs}
            obj['url'] = obj.get('url')
            urls.extend(obj['url'])
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

        self.databases, parsers = set(), set()
        self.sources_templates = defaultdict(list)

        # Populate lists of the databases used, the parsers and the sources
        for template in self.templates:
            template.validate()
            for parser in template.parser:
                parsers.add(parser)
            for source in template.source:
                self.sources_templates[source].append(template)
            for db in template.database:
                self.databases.add(db)

        # Map the templates to instances of these parser classes.
        self.parsers = {parser: parser() for parser in parsers}

        # Set the parsers in the templates themselves.
        for template in self.templates:
            template.prepare(self.parsers)

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
                        template.store_objects(objects, urls)
                        template.gen_source(objects)
                elif res == False:
                    logging.log(logging.INFO, 'stopping' + source.name)
                    empty.append(source)
                else:
                    continue
            if empty:
                for source in empty:
                    self.sources_templates.pop(source)
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
