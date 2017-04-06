from multiprocessing import Process, JoinableQueue
# from models.attr import Attr, Template
from queue import Empty
from pybloom import ScalableBloomFilter


class BaseParser(Process):
    '''
    This class implements the methods:
        _gen_source: generate a source if the template has that specified.
        _add_source: add a source to the current queue or
                     forward it to another run.
        _handle_empty
    which can all be overridden in subclasses.
    I
    '''
    def __init__(self, parent=None, templates=[], **kwargs):
        if not parent:
            raise Exception('No parent or run was specified')
        super(BaseParser, self).__init__()
        self.name = parent.name
        self.domain = parent.domain
        self.templates = templates
        self.in_q = JoinableQueue()
        self.source_q = parent.source_q
        self.store_q = parent.store_q
        self.db = parent.db
        self.seen = ScalableBloomFilter()
        self.forwarded = ScalableBloomFilter()
        self.forward_q = parent.forward_q
        self.to_parse = parent.to_parse
        self.parsed = 0
        self.average = []
        self.new_sources = []

        for key, value in kwargs.items():
            setattr(self, key, value)

    def run(self):
        while True:
            try:
                source = self.in_q.get(timeout=4)
            except Empty:
                print('timed out parser get')
                if self.parsed.value == self.to_parse.value:
                    with self.parsed.get_lock():
                        self.parsed.value = 0
                    break


            data = source.data
            self.seen.add(source.url)
            try:
                if getattr(self, '_prepare_data', None):
                    data = self._prepare_data(source)

                for template in self.templates:
                    extracted = self._extract(data, template)

                    template.objects = list(
                        self._gen_objects(template, extracted, source)
                    )

                    if template.preview:
                        print(template.objects[0])

                    if not template.objects and template.required:
                        print(template.selector, 'yielded nothing, quitting.')
                        self._handle_empty()

                    if template.db_type:
                        self.store_q.put(template.to_store())

                    for new_source in self.new_sources:
                        self._gen_source(*new_source)
                    del template.objects

            except Exception as E:
                print('parser error', E)

            with self.parsed.get_lock():
                self.parsed.value += 1

            if self.parsed.value == self.to_parse.value:
                with self.parsed.get_lock():
                    self.parsed.value = 0
                self.in_q.task_done()
                break

            self.in_q.task_done()

            # we have parsed the last source

    def _gen_objects(self, template, extracted, source):
        '''
        Create objects from parsed data using the functions
        defined in the scrape model. Also calls the functions
        that create the sources from Attrs or Templates (_gen_source,
        _source_from_object).
        '''

        for data in extracted:
            # Create a new objct from the template.
            objct = template._replicate(name=template.name, url=source.url)

            # Set predefined attributes from the source.
            for attr in source.attrs.values():
                objct.attrs[attr.name] = attr()

            no_value = 0

            # Set the attributes.
            for attr in self._gen_attrs(template.attrs.values(), objct, data):
                objct.attrs[attr.name] = attr

                if not attr.value:
                    no_value += 1

            # We want to count how many attrs return None
            # Don't return anything if we have no values for the attributes
            if no_value == len(objct.attrs) - len(source.attrs):
                print('Template {} has failed, attempting to use the fallback'.\
                      format(template.name))
                if getattr(self, '_fallback', None) and False:
                    for objct in self._fallback(template, extracted, source):
                        yield objct
                    continue
                else:
                    print('Template', template.name, 'failed')
                    print(data.text_content())
                    continue

            # Create a new Source from the template if desirable
            if template.source and getattr(self, '_source_from_object', None):
                objct.source = template.source()
                self._source_from_object(objct, source)

            yield objct

    def _gen_attrs(self, attrs, objct, data):
        for attr in attrs:
            if attr.selector:
                elements = attr.selector(data)
            else:
                elements = [data]

            # get the parse functions and recursively apply them.
            parse_funcs = [getattr(self, f, f) for f in attr.func]
            parsed = self._apply_funcs(elements, parse_funcs,
                                       attr.kws)
            if attr.type and type(parsed) != attr.type:
                print('Not the same type')

            # Create a request from the attribute if desirable
            if attr.source and parsed:
                self.new_sources.append((objct, attr, parsed))

            yield attr._replicate(name=attr.name, value=parsed)

    def _apply_funcs(self, elements, parse_funcs, kws):
        if type(kws) != list:
            kws = [kws]

        if len(parse_funcs) == 1 and hasattr(parse_funcs, '__iter__'):
            return parse_funcs[0](elements, **kws[0])
        elif type(parse_funcs) == str:
            return parse_funcs(elements, **kws[0])
        else:
            parsed = parse_funcs[0](elements, **kws[0])
            return self._apply_funcs(parsed, parse_funcs[1:],
                                     kws[1:] if kws else {})

    def _gen_source(self, objct, attr, parsed):
        if type(parsed) != list:
            parsed = [parsed]

        for value in parsed:
            # for now only "or" is supported.
            if attr.source_condition and \
                    not any(
                        self._evaluate_condition(objct,
                                                 attr.source_condition)
                    ):
                continue

            new_source = attr.source(
                url=self._apply_src_template(attr.source, value))

            if attr.attr_condition and \
                    self.value_is_new(objct, value, attr.attr_condition):
                    self._add_source(new_source)
            else:
                self._add_source(new_source)

    def value_is_new(self, objct, uri, name):
        db_objct = self.db.read(uri, objct)
        if db_objct and db_objct.attrs.get(name):
            if db_objct.attrs[name].value != objct.attrs[name].value:
                return True
            return False

    def _apply_src_template(self, source, url):
        if source.src_template:
            # use formatting notation in the src_template
            return source.src_template.format(url)
        return url

    def _value(self, parsed, index=None):
        if parsed:
            if len(parsed) == 1:
                return parsed[0]
            return parsed[index] if index else parsed

    def _evaluate_condition(self, objct, condition, **kwargs):
        # TODO add "in", and other possibilities.
        for name, cond in condition.items():
            if objct.attrs.get(name):
                values = objct.attrs[name].value
                # Wrap the value in a list without for example seperating the
                # characters.
                print(values)
                values = [values] if type(values) != list else values
            else:
                raise Exception('The attribute has not been set.')
            for val in values:
                if val and eval(str(val) + cond, {}, {}):
                    yield True
                else:
                    yield False

    def _add_source(self, source):
        if source.url and (source.url not in self.seen or source.duplicate) \
                and source.url not in self.forwarded:
            if source.active:
                with self.to_parse.get_lock():
                    self.to_parse.value += 1
                self.source_q.put(source)
                self.seen.add(source.url)
            else:
                self.forward_q.put(source)
                self.forwarded.add(source.url)

    def _handle_empty(self):
        while not self.in_q.empty():
            try:
                self.in_q.get(False)
            except Empty:
                continue
            self.source_q.task_done()
