from datetime import datetime
import csv
import json
import re
import logging

import lxml.html as lxhtml
from lxml.etree import XPath
from lxml.cssselect import CSSSelector, SelectorSyntaxError
from scrapely import Scraper

from .helpers import str_as_tuple, add_other_doc


class BaseParser:
    '''
    This class implements the methods:
        _gen_source: generate a source if the template has that specified.
        _add_source: add a source to the current queue or
                     forward it to another run.
    which can all be overridden in subclasses.
    I
    '''
    def __init__(self, parent=None, templates=[], **kwargs):
        if not parent:
            raise Exception('No parent or phase was specified')
        self.name = parent.name
        self.domain = parent.domain
        # Set all selectors and the functions of the attrs to the correct
        # functions and selectors of the parser.
        self._prepare_templates(templates)
        self.parent = parent

        for key, value in kwargs.items():
            setattr(self, key, value)

    def _convert_data(self, source):
        raise NotImplementedError

    def _extract(self, data, template):
        raise NotImplementedError

    def _apply_selector(self, selector, data):
        raise NotImplementedError

    def _get_selector(self, model):
        raise NotImplementedError

    def parse(self, source, template, selector=None, gen_objects=True):
        '''
        Generator that parses a source based on a template.
        If the source has a template, the data in the source is parsed
        according to that template.
        '''

        data = self._convert_data(source.data)

        # if source.templates:
        #    templates = source.templates
        # else:
        #    templates = self.templates

        extracted = self._extract(data, selector)
        if not extracted:
            logging.log(logging.WARNING, "{selector} selector of template: " +
                        "{name} returned no data".format(selector,
                                                         template.name))

        if not gen_objects:
            return self.to_string(extracted)
        objects = list(self._gen_objects(template, extracted, source))

        if not template.objects and template.required:
            print(template.selector, 'yielded nothing, quitting.')
            self.parent.reset_source_queue()

        return objects

    def _prepare_templates(self, templates):
        for template in templates:
            for attr in template.attrs.values():
                attr.func = self._get_funcs(attr.func)
                attr.selector = self._get_selector(attr.selector)

    def _get_funcs(self, func_names):
        functions = []
        try:
            if func_names:
                for f in func_names:
                    if type(f) != str:
                        functions.append(f)
                    else:
                        functions.append(getattr(self, f))
            return functions
        except:
            print(f)
        return tuple(getattr(self, f) for f in func_names)

    def _gen_objects(self, template, extracted, source):
        '''
        Create objects from parsed data using the functions
        defined in the scrape model. Also calls the functions
        that create the sources from Attrs or Templates (_gen_source,
        _source_from_object).
        '''
        for data in extracted:
            # Create a new objct from the template.
            objct = template._replicate(name=template.name, url=source.url,
                                        func=template.func)

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
                logging.log(
                    logging.WARNING, 'Template {} has failed, attempting to' + /
                    'use the fallback'.format(template.name))
                print(source.url)
                if getattr(self, '_fallback', None) and False:
                    for objct in self._fallback(template, extracted, source):
                        yield objct
                    continue
                else:
                    logging.log(logging.WARNING,
                                'Template' + template.name + 'failed')
                    logging.log(logging.WARNING, 'data:\n' + data.text_content())
                    continue

            # Create a new Source from the template if desirable
            if template.source and getattr(self, '_source_from_object', None):
                objct.source = template.source()
                self._source_from_object(objct, source)

            yield objct

    def _gen_attrs(self, attrs, objct, data):
        for attr in attrs:
            if not attr.func:
                new_attr = attr()
            else:
                elements = self._apply_selector(attr.selector, data)

                # get the parse functions and recursively apply them.
                parsed = self._apply_funcs(elements, attr.func, attr.kws)

                if attr.type and type(parsed) != attr.type:
                    logging.log(
                        logging.WARNING,
                        'Not the same type' + attr.name + attr.type +
                        str(parsed))

                new_attr = attr._replicate(name=attr.name, value=parsed,
                                           source=attr.source)

                # Create a request from the attribute if desirable
                if attr.source and parsed:
                    self.parent.new_sources.append((objct, new_attr))

            yield new_attr

    def _apply_funcs(self, elements, parse_funcs, kws):
        if len(parse_funcs) == 1 and hasattr(parse_funcs, '__iter__'):
            return parse_funcs[0](elements, **kws[0])
        else:
            parsed = parse_funcs[0](elements, **kws[0])
            return self._apply_funcs(parsed, parse_funcs[1:], kws[1:])

    def _value(self, parsed, index=None):
        if type(parsed) != list:
            parsed = list(parsed)
        if len(parsed) == 1:
            return parsed[0]
        return parsed[index] if index else parsed

    # TODO check if this belongs here...
    def _copy_attrs(self, objct, source):
        # Copy only the attribute with the key
        if type(source.copy_attrs) == str:
            if objct.attrs.get(source.copy_attrs):
                attr = objct.attrs[copy_attrs]._replicate()
                new_source.attrs[copy_attrs] = attr
            else:
                raise Exception('Could not copy attr', copy_attrs)

        # Copy a list of attributes
        elif hasattr(source.copy_attrs, 'iter'):
            for attr_name in source.copy_attrs:
                attr = objct.attrs.get(attr_name)
                if attr:
                    new_source.attrs[attr_name] = attr
                else:
                    raise Exception('Could not copy all attrs', copy_attrs)

        else: # Copy all the attributes.
            new_source.attrs = {key: attr._replicate() for key, attr in
                                objct.attrs.items()}
        return new_source

    def modify_text(self, text, replacers=None, substitute='', regex: str='',
                numbers: bool=False, needle=None):
        """
        replacers: string or list of values/regular expressions that have to be
            replaced in the text. Used in combination with substitute.
        substitute: the substitute used in the replacers parameter.
        """
        if replacers:
            replacers = str_as_tuple(replacers)
            regex = re.compile('|'.join(replacers))
            text = (regex.sub(substitute, t) for t in text)

        if regex:
            regex = re.compile(regex)
            text = (f for t in text for f in regex.findall(t))

        if needle:
            if not all([re.match(re.escape(needle), t) for t in text]):
                return [None]

        if numbers:
            text = [int(''.join([c for c in t if c.isdigit() and c]))
                    for t in text if t and any(map(str.isdigit, t))]
        return text

    def _sel_text(self, text, index=None, **kwargs):
        '''
        Selects and modifies text.
        '''
        stripped = (t.lstrip().rstrip() for t in text if t)
        text = self.modify_text(stripped, **kwargs)
        return self._value(text, index)


class HTMLParser(BaseParser):
    '''
    A parser that is able to parse html.
    '''
    def __init__(self, **kwargs):
        super(HTMLParser, self).__init__(**kwargs)
        self.scrapely_parser = None

    def _convert_data(self, data):
        try:  # Create an HTML object from the returned text.
            data = lxhtml.fromstring(data)
        except ValueError:  # This happens when xml is declared in html.
            data = lxhtml.fromstring('\n'.join(data.split('\n')[1:]))
        except TypeError:
            logging.log(logging.WARNING,
                        'Something weird has been returned by the server.')
            logging.log(logging.WARNING, data)
        data.make_links_absolute(self.domain)
        return data

    def _get_selector(self, selector):
        if selector:
            if type(selector) in (CSSSelector, XPath):
                return selector
            else:
                selector = ' '.join(selector).strip()
                try:
                    return CSSSelector(selector)
                except SelectorSyntaxError:
                    return XPath(selector)
                except:
                    raise Exception('Not a valid css or xpath selector',
                                    selector)
        return None

    def _apply_selector(self, selector, data):
        if selector:
            return selector(data)
        else:
            return (data,)

    def _extract(self, html, selector):
        if html is not None:
            extracted = self._apply_selector(selector, html)
        else:
            extracted = []
        return extracted

    def to_string(self, data):
        return ''.join(data.to_string())

    def _source_from_object(self, objct, source):
        # TODO fix that the source object can determine for itself where data
        # or params should be placed in the object.
        new_source = objct.source._replicate()
        attrs = {attr.name: attr.value for attr in objct.attrs.values()
                    if attr.name != 'url'}

        if not getattr(new_source, 'url', None):
            url = objct.attrs.get('url')

            if url and not isinstance(url, list):
                new_source.url = self.parent._apply_src_template(source,
                                                                 url.value)
            else:
                new_source.url = self.parent._apply_src_template(source,
                                                                 source.url)

        if new_source.copy_attrs:
            new_source = self._copy_attrs(objct, new_source)

        if new_source.parent:
            new_source.attrs['_parent'] = objct.attrs['url']._replicate()

        if new_source.method == 'post':
            new_source.data = {**new_source.data, **attrs} # noqa
        else:
            new_source.params = attrs

        self.parent._add_source(new_source)

    def _fallback(self, template, html, source):
        if not self.scrapely_parser:
            self.scrapely_parser = Scraper()

        html = self.scrapely_parser.HtmlPage(body=html)
        db_objct = self.db.read(uri, objct)
        if not db_objct:
            data = db_objct.attrs_to_dict()

            self.scrapely_parser.train_from_htmlpage(html, data)
            attr_dicts = self.scrapely_parser.scrape_page(html)

            for attr_dict in attr_dicts:
                objct = template._replicate(name=template.name, url=source.url)
                # Add the parsed values.
                objct.attrs_from_dict(attr_dict)
                yield objct
        return []

    def _convert_to_element(self, parsed):
        elements = []
        for p in parsed:
            if not type(p) == lxhtml.HtmlElement:
                elem = lxhtml.Element('p')
                elem.text = p
                elements.append(elem)
        return elements

    @add_other_doc(BaseParser.modify_text)
    def sel_text(self, elements, all_text=True, **kwargs):  # noqa
        '''
        Select all text for a given selector.
        '''
        if all_text:
            text = [el.text_content() for el in elements]
        else:
            text = [el.text for el in elements]
        return self._sel_text(text, **kwargs)

    def sel_table(self, elements, columns: int=2, offset: int=0):
        '''
        Parses a nxn table into a dictionary.
        Works best when the input is a td selector.
        Specify the amount of columns with the columns parameter.
        example:
            parse a 2x2 table
            {'func': sel_table,
            'params': {
                'selector': CSSSelector('table td'),
                'columns': 2,
                'offset': 0,
                }
            }
            leads to:
            sel_table(html=lxml.etree, selector=CSSSelector('table td'),
                    columns=2, offset=0)
        '''
        keys = [el.text for el in elements[offset::columns]]
        values = [el.text for el in elements[1::columns]]
        return dict(zip(keys, values))

    def sel_row(self, elements, row_selector: int=None, value: str='',
                attr=None, index=None):
        rows = [row for row in elements if value in row.text_contents()]
        if attr:
            selected = [sel for sel in sel_attr(row, row_selector)
                        for row in rows]
        else:
            selected = [sel for sel in sel_text(row, row_selector)
                        for row in rows]
        return self._value(selected, index)

    def sel_attr(self, elements, attr: str='', **kwargs):
        '''
        Extract an attribute of an HTML element. Will return
        a list of attributes if multiple tags match the
        selector.

        The **kwargs are the keyword arguments that can be added are from
        the BaseParser.modify_text method.
        '''

        attrs = (el.attrib.get(attr) for el in elements)
        return self._sel_text(attrs, **kwargs)

    def sel_url(self, elements, index: int=None, **kwargs):
        return self.sel_attr(elements, attr='href', index=index, **kwargs)

    def sel_date(self, elements, fmt: str='YYYYmmdd', attr: str=None, index:
                 int=None):
        '''
        Returns a python date object with the specified format.
        '''
        if attr:
            date = sel_attr(html, selector, attr=attr, index=index)
        else:
            date = sel_text(html, selector, index=index)
        if date:
            return datetime.strptime(date, fmt)

    def sel_exists(self, elements, key: str='', index: int=None):
        '''
        Return True if a keyword is in the selector text,
        '''
        text = self.sel_text(elements)
        if text:
            if key in text:
                return True
            return False

    def sel_raw_html(self, elements):
        return [el.raw_html for el in elements]

    def sel_js_array(self, elements, var_name='', var_type=None):
        var_regex = 'var\s*'+var_name+'\s*=\s*(?:new Array\(|\[)(.*)(?:\)|\]);'
        array_string = self.sel_text(elements, regex=var_regex)
        if array_string:
            if var_type:
                return list(map(var_type, array_string.split(',')))
            return array_string.split(',')

    def fill_form(self, elements, fields={}, attrs=[]):
        for form in elements:
            data = {**dict(form.form_values()), **fields}
            source = Source(url=form.action, method=form.method, duplicate=True,
                            attrs=attrs)
            if source.method == 'GET':
                source.params = data
            else:
                source.data = data
            self._add_source(source)


class JSONParser(BaseParser):
    def __init__(self, **kwargs):
        super(JSONParser, self).__init__(**kwargs)

    def _flatten(self, lis):
        new_list = []
        for item in lis:
            if type(item) == list:
                new_list.extend(self._flatten(item))
            else:
                new_list.append(item)
        return new_list

    def _convert_data(self, data):
        return json.loads(data)

    def _extract(self, data, selector):
        # TODO add the possibility to parse lists
        if selector:
            return self._apply_selector(selector, data)
        else:
            if type(data) != list:
                return [data]
            return data

    def to_string(self, data):
        return ''.join(data).encode('utf8')

    def _apply_selector(self, selector, data):
        while selector and data:
            cur_sel = selector[0]
            if type(data) == dict:
                if cur_sel in data:
                    data = data[cur_sel]
                else:
                    data = None
            elif type(data) == list:
                if type(cur_sel) == int:
                    data = data[cur_sel]
                else:
                    data = self._flatten(data)
                    data = [d.get(cur_sel, []) for d in data
                            if type(d) == dict]
            selector = selector[1:]
        if type(data) != list:
            return [data]
        return data

    def _get_selector(self, selector):
        return str_as_tuple(selector)

    @add_other_doc(BaseParser._sel_text)
    def sel_text(self, elements, **kwargs):  # noqa
        return self._sel_text(elements, **kwargs)

    def sel_dict(self, elements):
        return elements


class TextParser(BaseParser):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _convert_data(self, data):
        return data

    def _extract(self, data, template):
        return str_as_tuple(data)

    def _apply_selector(self, selector, data):
        if selector:
            return data.split(selector)
        return data

    def _get_selector(self, selector):
        return str_as_tuple(selector)

    @add_other_doc(BaseParser._sel_text)
    def sel_text(self, elements, **kwargs):
        """
        Selects the text from data.
        """
        return self._sel_text(elements, **kwargs)


class CSVParser(BaseParser):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _convert_data(self, data):
        return data

    def _extract(self, data, template):
        return [d.split(',') for d in data.split('\n') if d]

    def _apply_selector(self, selector, data):
        if selector:
            return [data[selector[0]]]
        return data

    def _get_selector(self, selector):
        return selector

    @add_other_doc(BaseParser._sel_text)
    def sel_text(self, elements, **kwargs):
        return self._sel_text(elements, **kwargs)
