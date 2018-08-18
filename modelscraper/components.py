from collections import defaultdict, ChainMap
from datetime import datetime
from itertools import zip_longest, chain
from functools import partial
import logging

import requests
import attr

from .sources import WebSource
from .parsers import HTMLParser
from .helpers import selector_converter, attr_dict, str_as_tuple, wrap_list
from . import databases
from .scrape_worker import ScrapeWorker, DummyScrapeWorker


@attr.s
class BaseModel(object):
    def _replicate(self, **kwargs):
        return self.__class__(**kwargs)

    def __call__(self, **kwargs):
        return self.__class__(**{**self.__dict__, **kwargs})  # noqa

@attr.s
class Phase(BaseModel):
    active = attr.ib(default=True)
    name = attr.ib(default='')
    n_workers = attr.ib(default=1)
    repeat = attr.ib(default=False)
    sources = attr.ib(default=attr.Factory(list))
    source_worker = attr.ib(default=WebSource)
    synchronize = attr.ib(default=False)
    templates = attr.ib(default=attr.Factory(list))
    parser = attr.ib(default=HTMLParser)
    save_raw = attr.ib(default=False)
    db_type = attr.ib(default=None)
    forwards = attr.ib(default=attr.Factory(list))

    def __attrs_post_init__(self):
        for template in self.templates:
            if not template.parser:
                template.parser = (self.parser,)

@attr.s
class Source(BaseModel):
    url = attr.ib('')
    attrs = attr.ib(attr.Factory(dict), convert=attr_dict,
                    metadata={'Attr': 1})
    func = attr.ib('get')
    kws = attr.ib(attr.Factory(dict))
    parse = attr.ib(True)
    src_template = attr.ib('{}')
    retries = attr.ib(10)
    duplicate = attr.ib(False)
    copy_attrs = attr.ib(None, convert=str_as_tuple)
    attr_condition = attr.ib('')
    parent = attr.ib(False)
    templates = attr.ib(attr.Factory(list))
    compression = attr.ib('')
    add_value = attr.ib('')
    extra_data = attr.ib(attr.Factory(dict))
    active = attr.ib(default=True)

    # TODO data passing between sources will be done by adding a selector
    def __attrs_post_init__(self):
        # Apply the source template
        if self.src_template:
            self.url = self.src_template.format(self.url)


    @classmethod
    def from_db(cls, template, url='url', query={}, **kwargs):
        db_type = template.db_type

        # Check if the database has been instantiated by the Scrapeworker
        if isinstance(db_type, type):
            db_type = db_type()
        for t in db_type.read(template=template, query=query):
            attr = t.attrs.get(url, [])
            if type(attr.value) is not list:
                values = [attr.value]
            else:
                values = attr.value
            for v in values:
                yield cls(url=v, **kwargs)

def source_conv(source):
    if type(source) in [list, Source]:
        return source
    elif source or type(source) is dict:
        return Source(**source) if type(source) is dict else Source()


@attr.s
class Attr(BaseModel):
    '''
    An Attr is used to hold a value for a template.
    This value is created by selecting data from the source using the selector,
    after which the "func" is called on the selected data.

    '''
    selector = attr.ib(default=None)
    name = attr.ib(default=None)
    value = attr.ib(default=None)
    func = attr.ib(default=None, convert=str_as_tuple,
                   metadata={'Phase.parser': 1})
    attr_condition = attr.ib(default={})
    source_condition = attr.ib(default={})
    source = attr.ib(default=None, convert=source_conv,
                     metadata={'Source': 1})
    kws = attr.ib(default=attr.Factory(dict))
    type = attr.ib(default=None)
    arity = attr.ib(default=1)
    forwarded = attr.ib(default=False)

    def __attrs_post_init__(self):
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
        print('state', state)
        self.__dict__.update(state)

    def gen_source(self, objects):
        for objct in objects:
            for value in objct.get(self.name, []):
                if self._evaluate_condition(objct):
                    attrs = self._copy_attrs(objct)
                    dup = self.source(url=value, attrs=attrs)
                    yield dup

    def set_func(self, parser):
        self.func = [partial(getattr(parser, func), **kw)
                    if type(func) == str
                    else func
                    for func, kw in zip(self.func, self.kws)]

    def _copy_attrs(self, objct):
        attrs = []
        if not self.source or not self.source.copy_attrs:
            print('not returning any attrs')
            return attrs
        assert all(attr in objct for attr in self.source.copy_attrs)
        if type(self.source.copy_attrs) == dict:
            # We store the copied attributes under different names.
            for key, value in self.source.copy_attrs.items():
                attrs.append(self._replicate(name=value, value=objct[key]))
        else:
            for key in self.source.copy_attrs:
                attrs.append(self._replicate(name=key, value=objct[key]))
        if self.source.parent:
            _parent = self._replicate(name='_parent',
                            value=(objct['_url'],))
            attrs.append(_parent)
        return attrs

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


@attr.s
class Template(BaseModel):
    db = attr.ib(default=None)
    table = attr.ib(default=None)
    db_type = attr.ib(default=None, convert=wrap_list)
    objects = attr.ib(default=attr.Factory(list))
    urls = attr.ib(default=attr.Factory(list))
    source = attr.ib(default=None, convert=source_conv)
    func = attr.ib(default='create')
    kws = attr.ib(default=attr.Factory(dict))
    name = attr.ib(default='')
    partial = attr.ib(default=False)
    required = attr.ib(default=False)
    selector = attr.ib(default=None)
    args = attr.ib(default=tuple)
    attrs = attr.ib(default=attr.Factory(dict), convert=attr_dict)
    url = attr.ib(default='')
    parser = attr.ib(default=False, convert=wrap_list)
    preparser = attr.ib(default=None)
    dated = attr.ib(default=False)

    def __attrs_post_init__(self):
        if self.url:
            self.attrs['url'] = Attr(name='url', value=self.url)

        if type(self.source) is list:
            for attr in self.source:
                self.attrs[attr].source = Source(active=False)

    def attrs_to_dict(self):
        return {a.name: a.value for a in self.attrs}

    def __getstate__(self):
        pickled = ['attrs', 'db', 'table', 'func', 'kws',
                   'name', 'url', 'objects', 'urls']
        return {p: self.__dict__[p] for p in pickled}

    def __setstate__(self, state):
        self.__dict__.update(state)

    def to_store(self):
        if self.db_type and self.objects:
            self.db_type.in_q.put(self)

    def gen_sources(self, objects):
        for attr in self.attrs:
            if attr.source:
                yield from attr.gen_source(objects)
        if self.source:
            if getattr(self.parser[-1], 'source_from_object', False):
                yield self.parser[-1].source_from_object(self, objct)

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
            if attr.forwarded:
                forwarded.append(attr.name)
            else:
                attr.set_func(parser)
                if attr.selector:
                    attr.selector = parser.get_selector(attr.selector)
        for attr in forwarded:
            self.attrs.pop(attr)

    def parse(self, source):
        if self.preparser:
            source.data = self.preparser(source.data)
        if len(self.parser) > 1:
            for parser, selector in zip(self.parser[:-1], self.selector[:-1]):
                source.data = parser.parse(source, self,
                                        selector=selector,
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
        for i, obj in enumerate(parser.parse(source, template=self,
                                             selector=selector)):
            count += i
            url = self.urls.extend(obj.get('url', obj.get('_url')))
            if self.dated:
                obj['_date'] = str(datetime.now())

            self.objects.append(obj)

        if not count and self.required:
            print(selector, 'yielded nothing, quitting.')
            return False
        return True

    def query(self, query={}):
        db_type = getattr(databases, db_type)
        if isinstance(db_type, type):
            db_type = db_type()
        yield from db_type().read(self,query=query)

    def all(self):
        yield from self.query()


class ScrapeModel:
    def __init__(self, name='', domain='', phases: Phase=[], num_getters=1,
                 time_out=1, user_agent=None, session=requests.Session(),
                 awaiting=False, cookies={}, schedule='', logfile='', **kwargs):
        # Set up the logging
        if logfile:
            logging.basicConfig(filename=logfile, level=logging.WARNING)

        self.name = name
        self.domain = domain
        self.phases = phases
        self.num_getters = num_getters
        self.time_out = time_out
        self.session = session
        self.awaiting = awaiting
        self.user_agent = user_agent
        self.schedule = schedule
        self.dbs = dict()

        if cookies:
            requests.utils.add_dict_to_cookiejar(self.session.cookies, cookies)

        for key, value in kwargs.items():
            setattr(self, key, value)
        db_threads, parsers = self.prepare_phases()

        # Map the templates to the correct database thread instance
        self.db_threads = defaultdict(list)
        for thread, templates in db_threads.items():
            db_thread = getattr(databases, thread)()
            db_thread.start()
            for template in templates:
                self.db_threads[template.name].append(db_thread)

        self.parsers = {parser: parser(parent=self) for parser in parsers}

        for phase in self.phases:
            for template in phase.templates:
                template.prepare(self.parsers)

    def run(self, dummy=False):
        if dummy:
            self.worker = DummyScrapeWorker(self)
        else:
            self.worker = ScrapeWorker(self)
        self.worker.run()

    def store_template(self, template):
        for db in self.db_threads.get(template.name, []):
            db.in_q.put(template)

    def kill_databases(self):
        print('Waiting for the database')
        for db in chain.from_iterable(self.db_threads.values()):
            print(db)
            db.in_q.put(None)
        for db in chain.from_iterable(self.db_threads.values()):
            print(db)
            db.join()

    def prepare_phases(self):
        '''
        Check if the functions in each template are used properly
        and return which types of databases are needed.
        '''
        db_threads = defaultdict(list)
        parsers = set()
        for phase in self.phases:
            for template in phase.templates:
                self.check_functions(template, phase)
                for parser in template.parser:
                    parsers.add(parser)
                if template.db_type:
                    for db_type in template.db_type:
                        db_threads[db_type].append(template)
        return db_threads, parsers

    def check_functions(self, template, phase):
        error_string = "One of these functions: {} is not implemented in {}."
        not_implemented = []

        for attr in template.attrs:
            if attr.func:
                for func in attr.func:
                    if type(func) is str and not getattr(phase.parser, func,
                                                         False):
                        not_implemented.append(func)

        if not_implemented:
            raise Exception(error_string.format(str(not_implemented),
                                                phase.parser.__class__.__name__))

    def get_template(self, template):
        if type(template) is Template:
            key = template.name
        elif type(template) is str:
            key = template
        for phase in self.phases:
            for template in phase.templates:
                if template.name == key:
                    return template

    def read_template(self, template_name='', as_object=False, *args):
        template = self.get_template(template_name)
        return template.db_type.read(*args, template=template)

    def __repr__(self):
        repr_string = self.name + ':\n'
        for phase in self.phases:
            repr_string += '\t{}\n'.format(phase.name)
            for template in phase.templates:
                repr_string += '\t\t{}\n'.format(template.name)
        return repr_string
