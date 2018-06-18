from datetime import datetime
import csv
import json
import re
import logging
from logging.handlers import QueueHandler
from queue import Queue
from urllib import parse as urlparse

import lxml.html as lxhtml
import lxml.etree as etree
from lxml.cssselect import CSSSelector
from cssselect import SelectorSyntaxError

from scrapely import Scraper
import xmljson

from .helpers import str_as_tuple, add_other_doc, wrap_list


logger = logging.getLogger(__name__)

class BaseParser:
    '''
    This class implements the methods:
        _gen_source: generate a source if the template has that specified.
        _add_source: add a source to the current queue or
                     forward it to another run.
    which can all be overridden in subclasses.
    '''

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _convert_data(self, source):
        raise NotImplementedError()

    def _extract(self, data, template):
        raise NotImplementedError()

    def _apply_selector(self, selector, data):
        raise NotImplementedError()

    def get_selector(self, selector):
        '''
        Get the selector to be the function which will get value from the source
        or a selector defined in a subclass.
        '''
        if hasattr(selector, '__iter__') and 'Source' in selector:
            selector = self._data_from_source
        else:
            return self._get_selector(selector)

    def _data_from_source(self, selector, *args):
        selector = selector.split('.')[-1]
        return self.source.extra_data.get(selector)

    def parse(self, source, template, selector=None, gen_objects=True):
        '''
        Generator that parses a source based on a template.
        If the source has a template, the data in the source is parsed
        according to that template.
        '''
        self.source = source
        data = self._convert_data(source)
        extracted = self._extract(data, selector)
        if not extracted:
            logging.log(logging.WARNING,
                        "{selector} selector of template: ".format(selector=selector) +
                        "{name} returned no data".format(name=template.name))
        if not gen_objects:
            return self.to_string(extracted)
        objects = list(self._gen_objects(template, extracted, source))

        if not objects and template.required:
            print(template.selector, 'yielded nothing, quitting.')
            source.duplicate = True
            self.parent._add_source(source)

        return objects

    def get_funcs(self, func_names):
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
            objct = {'_url': source.url}

            # Set predefined attributes from the source.
            for attr in source.attrs.values():
                objct[attr.name] = attr.value

            no_value = 0

            # Set the attributes.
            for name, value in self._gen_attrs(template.attrs, objct, data):
                objct[name] = value

                if not value:
                    logging.log(logging.WARNING, "no value for " + name +
                                "for template {template}".format(
                                    name=name, template=template.name))
                    no_value += 1

            # We want to count how many attrs return None
            # Don't return anything if we have no values for the attributes
            if no_value == len(objct) - len(source.attrs):
                if getattr(self, '_fallback', None) and False:
                    logging.log(logging.WARNING,
                                'Template {} has failed, attempting to' +
                                ' use the fallback'.format(template.name))
                    for objct in self._fallback(template, extracted, source):
                        yield objct
                    continue
                else:
                    logging.log(logging.WARNING,
                                'Template' + template.name + 'failed')
                    continue

            yield objct

    def _gen_attrs(self, attrs, objct, data):
        for attr in attrs:
            if not attr.func:
                parsed = attr.value
            elif attr.forwarded:
                print(attr)
                continue
            else:
                elements = self._apply_selector(attr.selector, data)
                parsed = self._apply_funcs(elements, attr.func, attr.kws)

                if attr.type and type(parsed) != attr.type:
                    logging.log(
                        logging.WARNING,
                        'Not the same type' + attr.name + attr.type +
                        str(parsed))
            yield attr.name, parsed

    def _apply_funcs(self, elements, parse_funcs, kws):
        if len(parse_funcs) == 1 and hasattr(parse_funcs, '__iter__'):
            return parse_funcs[0](elements, **kws[0])
        else:
            parsed = parse_funcs[0](elements, **kws[0])
            return self._apply_funcs(parsed, parse_funcs[1:], kws[1:])

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
                numbers: bool=False, needle=None, template=''):
        """
        replacers: string or list of values/regular expressions that have to be
            replaced in the text. Used in combination with substitute.
        substitute: the substitute used in the replacers parameter.
        """
        if replacers:
            text = map(replacers, text)

        if regex:
            regex = re.compile(regex)
            text = (f for t in text for f in regex.findall(t))

        if needle:
            matches = [re.match(re.escape(needle), t) for t in text]
            if not all(matches):
                return [None]

        if numbers:
            text = (int(''.join([c for c in t if c.isdigit() and c]))
                    for t in text if t and any(map(str.isdigit, t)))
        if template:
            text = (template.format(t) for t in text)
        return text

    def _sel_text(self, text, index=None, **kwargs):
        '''
        Selects and modifies text.
        '''
        stripped = (t.lstrip().rstrip() for t in text if t)
        text = self.modify_text(stripped, **kwargs)
        return self._value(text, index)

    def _value(self, parsed, index=None):
        if not parsed:
            return None
        if type(parsed) != list:
            parsed = list(parsed)
        try:
            return parsed[index] if index is not None else parsed
        except IndexError:
            print('not long enough', parsed)
            return parsed


class HTMLParser(BaseParser):
    '''
    A parser that is able to parse html.
    '''
    def __init__(self, *args, **kwargs):
        super(HTMLParser, self).__init__(*args, **kwargs)
        self.scrapely_parser = None

    def _convert_data(self, source):
        data = source.data
        try:  # Create an HTML object from the returned text.
            data = lxhtml.fromstring(data)
        except ValueError:  # This happens when xml is declared in html.
            data = lxhtml.fromstring('\n'.join(data.split('\n')[1:]))
        except TypeError:
            logging.log(logging.WARNING,
                        'Something weird has been returned by the server.')
            logging.log(logging.WARNING, data)
            return False
        except etree.XMLSyntaxError:
            logging.log(logging.WARNING,
                        'XML syntax parsing error:',)
            return False
        else:
            urlparsed = urlparse.urlparse(source.url)
            data.make_links_absolute(urlparsed.scheme + '://' + urlparsed.netloc)
            return data

    def _get_selector(self, selector):
        assert type(selector) is str, "selector is not a string %r" %selector
        if selector:
            if type(selector) in (CSSSelector, etree.XPath):
                return selector
            else:
                try:
                    return CSSSelector(selector)
                except SelectorSyntaxError:
                    try:
                        return etree.XPath(selector)
                    except etree.XPathSyntaxError:
                        raise Exception('Not a valid css or xpath selector',
                                        selector)

        return None

    def custom_func(self, elements, function, selector=""):
        elements = (lxhtml.fromstring(function(el)) for el in elements)
        if selector:
            selector = self.get_selector(selector)
            selected = [s for el in elements for s in selector(el)]
            return selected
        return list(elements)

    def _apply_selector(self, selector, data):
        if selector:
            result = selector(data)
            return result
        return (data,)

    def _extract(self, html, selector):
        return self._apply_selector(selector, html)

    def to_string(self, data):
        return ''.join([lxhtml.tostring(d) for d in data])

    def _source_from_object(self, template, objct, source):
        # TODO fix that the source object can determine for itself where data
        # or params should be placed in the object.
        attrs = {name: value for name, value in objct.items() if name != 'url'}
        url = objct.get('url')
        if not url:
            logging.log(logging.WARNING, template.name + ' does not have a ' +
                        'url attribute.')
        else:
            new_source = template.source._replicate(url=url[0])
            if source.parent:
                new_source.attrs['_parent'] = objct['_url']
            if source.method == 'post':
                new_source.data = {**new_source.data, **attrs} # noqa
            else:
                new_source.params = attrs
            return new_source

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

    def _convert_to_element(self, parsed, elem_type='p'):
        elements = []
        for p in parsed:
            if not type(p) == lxhtml.HtmlElement:
                elem = lxhtml.Element(elem_type)
                elem.text = p
                elements.append(elem)
        return elements

    @add_other_doc(BaseParser.modify_text)
    def sel_text(self, elements, all_text=True, **kwargs):  # noqa
        '''
        Select all text for a given selector.
        '''
        if all_text:
            text = (el.text_content() for el in elements)
        else:
            text = (el.text for el in elements)
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

    @add_other_doc(BaseParser.modify_text)
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

    @add_other_doc(BaseParser.modify_text)
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
        array_string = self.sel_text(elements, regex=var_regex, index=0)
        if array_string:
            if var_type:
                return list(map(var_type, array_string.split(',')))
            return array_string.split(',')

    def fill_form(self, elements, fields={}, attrs=[]):
        from .components import Source
        for form in elements:
            data = {**dict(form.form_values()), **fields}
            source = Source(url=form.action, method=form.method, duplicate=True,
                            attrs=attrs)
            if source.method == 'GET':
                source.params = data
            else:
                source.data = data
            self.parent._add_source(source)

class JSONParser(HTMLParser):
    def _convert_data(self, source):
        xml = xmljson.badgerfish.etree(json.loads(source.data),
                                       root=etree.Element('root'))
        return xml

    def sel_text(self, elements, **kwargs):
        return self._sel_text((el.text for el in elements), **kwargs)

    def to_string(self, data):
        data = (etree.tostring(d).decode() for d in data)
        data = (d.replace('&gt;', '>').replace('&lt;', '<') for d in data)
        return ''.join(data)

class TextParser(BaseParser):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _convert_data(self, source):
        return source.data

    def _extract(self, data, selector):
        if selector:
            return ((d for d in self._apply_selector(sel, data))for sel in
                    selector)
        return str_as_tuple(data)

    def _apply_selector(self, selector, data):
        if selector:
            return data.split(selector)
        return data

    def get_selector(self, selector):
        return str_as_tuple(selector)

    @add_other_doc(BaseParser._sel_text)
    def sel_text(self, elements, **kwargs):
        """
        Selects the text from data.
        """
        return self._sel_text(str_as_tuple(elements), **kwargs)


class CSVParser(BaseParser):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _convert_data(self, source):
        return source.data

    def _extract(self, data, selector):
        return [d.split(',') for d in data.split('\n') if d]

    def _apply_selector(self, selector, data):
        if selector:
            return [data[selector]]
        return data

    def _get_selector(self, selector):
        return selector

    @add_other_doc(BaseParser._sel_text)
    def sel_text(self, elements, **kwargs):
        return self._sel_text(elements, **kwargs)


class XMLParser(HTMLParser):
    """
    A parser that can parse normal XML and escaped XML.
    Contains all the functions in the HTMLParser.
    """
    def __init__(self, parse_escaped=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parse_escaped = parse_escaped

    def _convert_data(self, source):
        data = source.data.rstrip().lstrip()
        # Remove escaped xml
        if self.parse_escaped:
            data = data.replace('&lt;', '<').replace('&gt;', '>')

        try:
            etree.fromstring(data)
        except TypeError:
            logging.log(logging.WARNING,
                        'Something weird has been returned by the server.')
            logging.log(logging.WARNING, data)
            return False
        except etree.XMLSyntaxError:
            logging.log(logging.WARNING,
                        'XML syntax parsing error:',)
            return False

        urlparsed = urlparse.urlparse(source.url)
        data.make_links_absolute(urlparsed.scheme + '://' + urlparsed.netloc)
        return data
