from collections import defaultdict
from itertools import zip_longest

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


    def __attrs_post_init__(self):
        for template in self.templates:
            if not template.parser:
                template.parser = (self.parser,)

@attr.s
class Source(BaseModel):
    url = attr.ib('')
    active = attr.ib(True)
    attrs = attr.ib(attr.Factory(dict), convert=attr_dict, metadata={'Attr': 1})
    method = attr.ib('get')
    parse = attr.ib(True)
    headers = attr.ib(attr.Factory(dict))
    data = attr.ib(default='')
    params = attr.ib(attr.Factory(dict))
    src_template = attr.ib('{}')
    retries = attr.ib(10)
    duplicate = attr.ib(False)
    copy_attrs = attr.ib(None, convert=str_as_tuple)
    attr_condition = attr.ib('')
    parent = attr.ib(False)
    from_db = attr.ib(None, metadata={'Template': 1})
    templates = attr.ib(attr.Factory(list))
    compression = attr.ib('')

    def __attrs_post_init__(self):
        # Apply the source template
        if self.src_template:
            self.url = self.src_template.format(self.url)

    @classmethod
    def from_db(cls, template, url='url', query=''):
        db_type = template.db_type
        for t in db_type().read(template=template, query=query):
            value = t.attrs.get(url, [])
            if type(value) is list:
                for v in value:
                    yield cls(url=v)
            else:
                yield cls(url=value)

def source_conv(source):
    if type(source) in [list, Source]:
        return source
    elif source or type(source) is dict:
        print(source)
        return Source(**source) if type(source) is dict else Source()


@attr.s
class Attr(BaseModel):
    '''
    An Attr is used to hold a value as an attribute for a template.
    The value for the attribute is obtained by applying the func
    on the element obtained through the selector.
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

    def __attrs_post_init__(self):
        # Ensure that the kws are encapsulated in a list with the same length
        # as the funcs.
        if self.func:
            self.kws = wrap_list(self.kws)
            difference = len(self.func) - len(self.kws)
            if difference:
                self.kws = [*self.kws, *[{} for _ in range(difference)]]

    def __call__(self, **kwargs):
        new_kws = kwargs.get('kws')
        if new_kws:
            new_kws = wrap_list(new_kws)
            kwargs['kws'] = [{**old, **new} for new, old in
                            zip_longest(new_kws, self.kws, fillvalue={})]
        return self.__class__(**{**self.__dict__, **kwargs})  # noqa

    def gen_source(self, objects):
        for objct in objects:
            for value in objct.get(self.name, []):
                if self._evaluate_condition(objct):
                    attrs = self._copy_attrs(objct)
                    dup = self.source(url=value, attrs=attrs)
                    yield dup

    def _copy_attrs(self, objct):
        attrs = []
        if not self.source or not self.source.copy_attrs:
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
    db_type = attr.ib(default=None)
    objects = attr.ib(init=False)
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

    def __attrs_post_init__(self):
        if type(self.db_type) is str and self.db_type and self.db:
            database_class = getattr(databases, self.db_type)
            if database_class:
                self.db_type = database_class
            else:
                raise Exception(self.db + 'This database is not supported')

        if self.url:
            self.attrs['url'] = Attr(name='url', value=self.url)

        if type(self.source) is list:
            for attr in self.source:
                self.attrs[attr].source = Source(active=False)

    def attrs_to_dict(self):
        return {a.name: a.value for a in self.attrs}

    def to_store(self):
        if self.db_type:
            replica = self.__class__(
                db=self.db, table=self.table, func=self.func, kws=self.kws,
                name=self.name, url=self.url)

            if self.objects:
                replica.objects = self.objects[:]
            self.db_type.in_q.put(replica)

    def gen_sources(self):
        for attr in self.attrs:
            if attr.source:
                yield from attr.gen_source(self.objects)
        if self.source:
            if getattr(self.parser[-1], 'source_from_object', False):
                yield self.parser[-1].source_from_object(self, objct)

    def attrs_from_dict(self, attrs):
        self.attrs = attr_dict((Attr(name=name, value=value) for
                      name, value in attrs.items()))

    def add_attr(self, attr):
        attr = Attr(name=name, value=value, **kwargs)
        self.attrs[attr.name] = attr

    def prepare(self, parsers):
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
        for attr in self.attrs:
            attr.func = parser.get_funcs(attr.func)
            if attr.selector:
                attr.selector = parser.get_selector(attr.selector)

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
        # Create the actual objects
        self.objects = parser.parse(source, template=self, selector=selector)

    @staticmethod
    def from_table(self, db_type, db, table, query=''):
        db_type = getattr(databases, db_type)
        yield from db_type().read(
            self.__class__(db_type=db_type, table=table, db=db),
            query=query
        )


class ScrapeModel:
    def __init__(self, name='', domain='', phases: Phase=[], num_getters=1,
                 time_out=1, user_agent=None, session=requests.Session(),
                 awaiting=False, cookies={}, schedule='',
                 dummy=False, **kwargs):
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
        self.new_sources = []

        if cookies:
            print(cookies)
            requests.utils.add_dict_to_cookiejar(self.session.cookies, cookies)

        for key, value in kwargs.items():
            setattr(self, key, value)
        db_threads, parsers = self.prepare_phases()
        self.set_db_threads(db_threads)

        self.parsers = {parser: parser(parent=self) for parser in parsers}

        for phase in self.phases:
            for template in phase.templates:
                template.prepare(self.parsers)

        if dummy:
            self.worker = ScrapeWorker(self)
        else:
            self.worker = DummyScrapeWorker(self)

    def run(self):
        self.worker.run()

    def set_db_threads(self, db_threads):
        self.db_threads = set()
        for thread, templates in db_threads.items():
            store_thread = thread()

            for template in templates:
                template.db_type = store_thread
            self.db_threads.add(store_thread)

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
                    db_threads[template.db_type].append(template)
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
