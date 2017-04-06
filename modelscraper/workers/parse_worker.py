from threading import Thread
from queue import Queue
import re
import json
import lxml.html as lxhtml
import time
from models import Attr, Template, Getter


class ParseWorker(Thread):
    '''
    A generic parser that executes the functions specified in the
    self.css variable. For use without parent Thread supply keyword
    arguments:
        name = str,
        domain = str,
        next_q = queue.Queue(),
        store_q = queue.Queue(),

    The ParseWorker expects the following tuple to be present in the queue:
        (url_meta[dict], html[str], url[str])
    '''
    def __init__(self, parent=None, objects=dict, raw_html=dict,
                 next_q=Queue(), **kwargs):
        super(ParseWorker, self).__init__()
        if parent or kwargs and next_q:
            self.parent = parent
            self.name = parent.name
            self.domain = parent.domain
            # self.templates = templates
            self.raw_html = raw_html
            self.get_q = Queue()
            self.next_q = parent.get_q
            self.output_q = parent.output_q
            self.seen = set()
            self.forward = set()
            self.average = []
            self.parsed = 0

        else:
            raise Exception('Not enough specified, please read the docstring')

        for key, value in kwargs.items():
            setattr(self, key, value)

    def run(self):
        while True:
            item = self.get_q.get()
            if item is None:
                break

            getter = item
            self.seen.add(getter.url)

            html = lxhtml.fromstring(getter.got)
            html.make_links_absolute(self.domain)

            start = time.time()
            for template in self.templates:
                to_store = template.store
                selected = self._get_selected(html, template)

                if template.store:
                    to_store.objects = self.make_objects(template,
                                                         selected, getter)

                    if not to_store.objects and template.required:
                        print('nothing found')
                        self._handle_empty()
                    self.output_q.put(to_store)
                else:
                    self.make_objects(template, selected, getter)
            took = time.time() - start
            self.average.append(took)
            self.get_q.task_done()

    def _get_selected(self, html, template):
        if not template.js_regex:
            selected = template.selector(html) if template.selector else [html]
        else:
            regex = re.compile(template.js_regex)
            selected = []
            # Find all the scripts that match the regex.
            scripts = (regex.findall(s.text_content())[0] for s in
                       html.cssselect('script')
                       if regex.search(s.text_content()))

            # Set selected to the scripts
            for script in scripts:
                selected.extend(json.loads(script))
        return selected

    def make_objects(self, template, selected, getter):
        objects = []
        # print('aantal links', len(selected))
        for sel in selected:
            objct = Template(name=template.name)
            objct.url = getter.url

            # Set predefined attributes from the getter.
            #print('aantal attrs', len(getter.attrs))
            for attr in getter.attrs:
                objct.attrs.append(attr.duplicate())

            # Set the attribute values
            for temp_attr in template.attrs:
                parsed = temp_attr.func(sel, temp_attr.selector,
                                        **temp_attr.kws)
                attr = Attr(name=temp_attr.name, value=parsed)
                objct.attrs.append(attr)

                # Create a request from the attribute if desirable
                if temp_attr.getter and parsed:
                    if type(parsed) != list:
                        parsed = [parsed]

                    for value in parsed:
                        new_getter = Getter(**temp_attr.getter)
                        new_getter.url = value
                        self._handle_getter(new_getter)

            if template.getter:
                self._handle_object_getter(objct)
            objects.append(objct)
        return objects

    def _handle_object_getter(self, objct):
        getter = objct.getter
        url_params = {attr.name: attr.value for attr in objct.attrs}

        if getter.method == 'post':
            getter.data = url_params
        else:
            getter.params = url_params
        self._handle_getter(objct.getter, url_params)

    def _handle_getter(self, getter):
        if getter.url and getter.url not in self.seen:
            if getter.active:
                self.next_q.put(getter)
            else:
                self.forward.add(getter)

        self.seen.add(getter.url)

    def _handle_empty(self):
        '''
        Gracefull shutdown if no more objects are found.
        with self.next_q.mutex:
            print('clearing')
            self.next_q.queue.clear()
            self.get_q.queue.clear()

            for _ in self.parent.get_workers:
                self.next_q.put(None)
            self.get_q.put(None)
            '''

        while not self.next_q.empty():
            try:
                self.next_q.get(False)
            except Empty:
                continue
            self.next_q.task_done()
