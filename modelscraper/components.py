from collections import defaultdict, ChainMap
from datetime import datetime
from itertools import zip_longest, chain
from functools import partial
import logging

import attr

from .parsers import HTMLParser
from .helpers import selector_converter, attr_dict, str_as_tuple, wrap_list
from . import databases
#from .scrape_worker import ScrapeWorker, DummyScrapeWorker


@attr.s
class BaseModel(object):
    emits = attr.ib(default=None)
    kws = attr.ib(default=attr.Factory(dict))
    name = attr.ib(default=None)
    selector = attr.ib(default=None)

    def _replicate(self, **kwargs):
        return self.__class__(**kwargs)

    def __call__(self, **kwargs):
        return self.__class__(**{**self.__dict__, **kwargs})  # noqa

@attr.s
class Attr(BaseModel):
    '''
    An Attr is used to hold a value for a template.
    This value is created by selecting data from the source using the selector,
    after which the "func" is called on the selected data.

    '''
    func = attr.ib(default=None, convert=str_as_tuple)
    value = attr.ib(default=None)
    attr_condition = attr.ib(default={})
    source_condition = attr.ib(default={})
    type = attr.ib(default=None)
    arity = attr.ib(default=1)
    from_source = attr.ib(default=False)
    transfers = attr.ib(False)

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
        self.__dict__.update(state)

    # Pass the attrs along as dicts in copy attrs
    def gen_source(self, objects, transfers):
        for objct in objects:
            if self._evaluate_condition(objct):
                urls = objct.get(self.name, [])
                yield urls

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


@attr.s
class Template(BaseModel):
    attrs = attr.ib(default=attr.Factory(dict), convert=attr_dict)
    dated = attr.ib(default=False)
    db = attr.ib(default=None)
    db_type = attr.ib(default=None, convert=wrap_list)
    func = attr.ib(default='create')
    objects = attr.ib(default=attr.Factory(list))
    parser = attr.ib(default=HTMLParser, convert=wrap_list)
    preparser = attr.ib(default=None)
    required = attr.ib(default=False)
    source = attr.ib(default=None)
    table = attr.ib(default=None)
    url = attr.ib(default='')
    urls = attr.ib(default=attr.Factory(list))

    def __attrs_post_init__(self):
        if self.url:
            self.attrs['url'] = Attr(name='url', value=self.url)

        self.validate()
        self.emit_attrs = [attr for attr in self.attrs
                           if attr.emits]
        self.transfers = [attr.name for attr in self.attrs
                          if attr.transfers]

    def validate(self):
        # Validate the functions of the attrs
        for parser in self.parser:
            for attr in [a for a in self.attrs if not a.from_source]:
                for func in attr.func:
                    if not getattr(parser, func, False):
                        raise Exception(
                            '{} does not exist in {}'.format(
                                func, parser.__name__))

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

    def gen_source(self, objects):
        for attr in self.emit_attrs:
            for objct in objects:
                if attr._evaluate_condition(objct):
                    for url in objct[attr.name]:
                        attrs = {key: objct[key] for key in self.transfers}
                        attr.emits.add_source(url, attrs)

        # TODO fix this to new spec
        #if self.emits:
        #    if getattr(self.parser[-1], 'source_from_object', False):
        #        yield self.parser[-1].source_from_object(self, objct)

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

    def parse(self, url, attrs, data):
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
            obj['url'] = obj.get('url', [obj.get('_url')])
            self.urls.extend(obj['url'])
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
    def __init__(self, name='', templates=[], num_getters=1,
                  awaiting=False, schedule='', logfile='', **kwargs):
        # Set up the logging
        if logfile:
            logging.basicConfig(filename=logfile, level=logging.WARNING)

        self.name = name
        self.templates = templates
        self.num_getters = num_getters
        self.awaiting = awaiting
        self.schedule = schedule
        self.dbs = dict()
        self.sources = {}

        # if cookies:
        #     requests.utils.add_dict_to_cookiejar(self.session.cookies, cookies)

        for key, value in kwargs.items():
            setattr(self, key, value)
        db_threads, parsers, sources = self.prepare_templates()

        # Map the templates to the correct database thread instance
        self.db_threads = defaultdict(list)
        for thread, templates in db_threads.items():
            db_thread = getattr(databases, thread)()
            db_thread.start()
            for template in templates:
                self.db_threads[template.name].append(db_thread)

        self.parsers = {parser: parser(parent=self) for parser in parsers}

        for template in self.templates:
            template.prepare(self.parsers)

        self.sources_templates = defaultdict(list)
        for template in self.templates:
            self.sources_templates[template.source].append(template)

    def run(self, dummy=False):
        while self.sources_templates:
            empty = []
            for source, templates in self.sources_templates.items():
                for res in source:
                    print('got from', source.name, res)
                    if res:
                        for template in templates:
                            template.parse(*res)
                            print(template.name, template.objects)
                            template.gen_source(template.objects)
                            self.store_template(template)
                    elif res is None:
                        empty.append(source)
            if empty:
                for source in empty:
                    print(source.name, 'deleted')
                    source.in_q.put(None)
                    self.sources_templates.pop(source)
        self.kill_databases()
        print('done')

    def store_template(self, template):
        for db in self.db_threads.get(template.name, []):
            db.in_q.put(template)

    def kill_databases(self):
        print('Waiting for the database')
        for db in chain.from_iterable(self.db_threads.values()):
            db.in_q.put(None)
        for db in chain.from_iterable(self.db_threads.values()):
            db.join()

    def prepare_templates(self):
        '''
        Check if the functions in each template are used properly
        and return which types of databases are needed.
        '''
        db_threads = defaultdict(list)
        parsers = set()
        sources = []

        for template in self.templates:
            for parser in template.parser:
                parsers.add(parser)
            if template.db_type:
                for db_type in template.db_type:
                    db_threads[db_type].append(template)
            for attr in template.attrs:
                if attr.emits:
                    sources.append(attr.emits)
        return db_threads, parsers, sources

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
