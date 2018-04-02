from collections import defaultdict
from itertools import zip_longest

import requests
import attr

from .sources import WebSource
from .parsers import HTMLParser
from .helpers import selector_converter, attr_dict, str_as_tuple, wrap_list
from . import databases


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
    data = attr.ib(attr.Factory(dict))
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
            self.url = self.source_template.format(self.url)

def source_conv(source):
    if source:
        if type(source) == Source:
            return source
        return Source(**source) if type(source) == dict else Source()


@attr.s
class Attr(BaseModel):
    '''
    An Attr is used to hold a value as an attribute for a template.
    The value for the attribute is obtained by applying the func
    on the element obtained through the selector.
    '''
    selector = attr.ib(default=None, convert=str_as_tuple)
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


@attr.s()
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
    selector = attr.ib(default=None, convert=str_as_tuple)
    args = attr.ib(default=tuple)
    attrs = attr.ib(default=attr.Factory(dict), convert=attr_dict)
    url = attr.ib(default='')
    parser = attr.ib(default=False, convert=wrap_list)
    _store_worker = attr.ib(init=False)

    def __attrs_post_init__(self):
        if self.db and not self.table:
            raise Exception(self.name +
                'Database name is set, but not the table')

        if self.url:
            self.attrs['url'] = Attr(name='url', value=self.url)

    def to_dict(self):
        return {'url': self.url, **self.attrs_to_dict()} # noqa

    def attrs_to_dict(self):
        return {a.name: a.value for a in self.attrs}

    def to_store(self):
        if self._store_worker:
            replica = self.__class__(db=self.db, table=self.table, func=self.func,
                                    db_type=self.db_type, kws=self.kws,
                                    name=self.name, url=self.url)
            if self.objects:
                replica.objects = self.objects[:]
            self._store_worker.store_q.put(replica)

    def attrs_from_dict(self, attrs):
        self.attrs = attr_dict((Attr(name=name, value=value) for
                      name, value in attrs.items()))

    def add_attr(self, attr):
        attr = Attr(name=name, value=value, **kwargs)
        self.attrs[attr.name] = attr

    def parse(self, source):
        if len(self.parser) > 1:
            i = 0
            while i < len(self.parser) - 1:
                parser = self.parser[i]
                selector = self.selector[i]
                source.data = parser.parse(source, self,
                                        selector=selector,
                                        gen_objects=False)
                i += 1

            parser = self.parser[i]
            if self.selector:
                selector = self.selector[i]
            else:
                selector = None
        else:
            parser = self.parser[0]
        # Create the actual objects
        self.objects = parser.parse(source, template=self,
                                selector=self.selector)

    '''
    def __repr__(self):
        repr_string = self.name
        if self.objects:
            for objct in self.objects:
                repr_string = "Template {}:\n".format(objct.name)
                for attr in objct.attrs:
                    repr_string += "\t{}: {}\n".format(attr.name, attr.value)
        return repr_string
    '''

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
                template.parser = [self.parsers[p] for p in template.parser]
                # TODO Fix the right selector with the right parser.
                if template.selector and len(template.parser) > 1:
                    template.selector = [parser._get_selector([selector])
                                        for parser, selector in
                                        zip(template.parser, template.selector)]
                else:
                    template.selector = template.parser[0]._get_selector(
                        template.selector)
            template.parser[-1]._prepare_templates(phase.templates)

    def set_db_threads(self, db_threads):
        self.db_threads = set()
        for thread, templates in db_threads.items():
            store_thread = getattr(databases, thread)()

            for template in templates:
                template._store_worker = store_thread
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
                    if not getattr(phase.parser, func, False):
                        not_implemented.append(func)

        if not_implemented:
            raise Exception(error_string.format(str(not_implemented),
                                                phase.parser.__class__.__name__))

    def get_template(self, key):
        for phase in self.phases:
            for template in phase.templates:
                if template.name == key:
                    return template

    def read_template(self, template_name='', as_object=False, *args):
        template = self.get_template(template_name)
        database = getattr(databases, template.db_type)()
        return database.read(*args, template=template)

    def __repr__(self):
        repr_string = self.name + ':\n'
        for phase in self.phases:
            repr_string += '\t{}\n'.format(phase.name)
            for template in phase.templates:
                repr_string += '\t\t{}\n'.format(template.name)
        return repr_string
