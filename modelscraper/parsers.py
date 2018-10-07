from datetime import datetime
import csv
import json
import re
import logging
from functools import partial
from logging.handlers import QueueHandler
from queue import Queue
from urllib import parse as urlparse
from functools import singledispatch

import lxml.html as lxhtml
import lxml.etree as etree
from lxml.cssselect import CSSSelector
from cssselect import SelectorSyntaxError

from scrapely import Scraper
import xmljson

from .helpers import str_as_tuple, add_other_doc, wrap_list
from .selectors import ORCSSSelector


logger = logging.getLogger(__name__)


class BaseParser(object):
    '''
    This class implements the methods:
        _gen_source: generate a source if the template has that specified.
        _add_source: add a source to the current queue or
                     forward it to another run.
    which can all be overridden in subclasses.
    '''
    def _convert_data(self, source):
        raise NotImplementedError()

    def select(self, selector=None):
        selector = self._get_selector(selector)
        return partial(self._select, selector=selector)

    def _select(self, url, data, selector=None):
        data = self._convert_data(url, data)
        if selector:
            result = selector(data)
            return result
        return (data,)

    def _modify_text(self, text, replacers=None, substitute='', regex: str='',
                numbers: bool=False, needle=None, template=''):
        """
        replacers: string or list of values/regular expressions that have to be
            replaced in the text. Used in combination with substitute.
        substitute: the substitute used in the replacers parameter.
        """
        if replacers:
            for key, subsitute in zip(replacers, substitute):
                text = text.replace(key, substitute)

        if regex:
            regex = re.compile(regex)
            try:
                text = [found for found in regex.findall(text)]
            except:
                print('regex error', text)

        if needle:
            matches = re.match(re.escape(needle), text)
            if not matches:
                return None

        if numbers and any(map(str.isdigit, text)):
            text = int(''.join([c for c in text if c.isdigit() and c]))

        if template:
            text = template.format(text)
        return text

    def text(self, selector=None, **kwargs):
        selector = self._get_selector(selector)
        return partial(self._text, selector=selector, **kwargs)

    def _text(self, url, data, selector=None, index=None, **kwargs):
        '''
        Selects and modifies text.
        '''
        for element in self._select(url, data, selector):
            stripped = element.lstrip().rstrip()
            text = self._modify_text(stripped, **kwargs)
            yield text

    def exists(self, selector=None, key: str='', **kwargs):
        '''
        Return True if a keyword is in the selector text,
        '''
        selector = self._get_selector(selector)
        return partial(self._exists, selector=selector, key=key,
                       **kwargs)

    def _exists(self, url, data, selector=None, key='', **kwargs):
        text = self._text(url, data, selector=selector, **kwargs)
        if text:
            for t in text:
                if key in t:
                    yield True
                yield False


class HTMLParser(BaseParser):
    '''
    A parser that is able to parse both XML and HTML.
    '''

    data_types = (lxhtml.HtmlElement, etree._Element)
    def __init__(self, parse_escaped=True):
        super().__init__()
        self.scrapely_parser = None
        self.parse_escaped = parse_escaped

    def _convert_data(self, url, data):
        if type(data) in self.data_types:
            return data
        else:
            data = data.rstrip().lstrip()
            # Replace escaped tags
            if self.parse_escaped:
                data = data.replace('&lt;', '<').replace('&gt;', '>')

            try:  # Create an HTML object from the returned text.
                data = lxhtml.fromstring(data)
            except ValueError:  # This happens when xml is declared in html.
                try:
                    data = lxhtml.fromstring('\n'.join(data.split('\n')[1:]))
                except Exception:
                    raise

            except TypeError:
                logging.log(logging.WARNING,
                            'Something weird has been returned by the server.')
                logging.log(logging.WARNING, data)
                return False

            except etree.XMLSyntaxError:
                logging.log(logging.WARNING,
                            'XML syntax parsing error:',)
                return False

            except Exception:
                raise

            urlparsed = urlparse.urlparse(url)
            data.make_links_absolute(urlparsed.scheme + '://' + urlparsed.netloc)
        return data

    def _get_selector(self, selector):
        if selector:
            if type(selector) in (CSSSelector, ORCSSSelector, etree.XPath):
                return selector
            else:
                assert type(selector) is str, "selector is not a string %r" %selector
                try:
                    return CSSSelector(selector)
                except SelectorSyntaxError:
                    try:
                        return etree.XPath(selector)
                    except etree.XPathSyntaxError:
                        raise Exception('Not a valid css or xpath selector',
                                        selector)

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

    def custom_func(self, selector=None, function=None):
        selector = self._get_selector(selector)
        return partial(self._custom_func, selector=selector, function=function)

    def _custom_func(self, url, data, selector=None, function=None):
        return function(element)

    @add_other_doc(BaseParser._text)
    def text(self, selector=None, all_text=True, **kwargs):
        selector = self._get_selector(selector)
        return partial(self._text, selector=selector, all_text=True, **kwargs)

    def _text(self, url, data, selector=None, all_text=True, **kwargs):
        for element in self._select(url, data, selector):
            if type(element) != str:
                if all_text:
                    text = element.text_content()
                else:
                    text = element.text
            else:
                text = element
            yield self._modify_text(text, **kwargs)

    def table(self, selector=None):
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
        selector = self._get_selector(selector)
        return partial(self._table, selector=selector)

    def _table(self, url, data, selector=None):
        for element in self._select(url, data, selector):
            table_headers = [header.text_content() for header in
                             element.cssselect('th')]
            columns = len(table_headers)
            table_elements = [cell.text_content() for cell in
                              element.cssselect('td')]
            rows = list(zip(*[iter(table_elements)]*columns))
            yield rows


    @add_other_doc(BaseParser._modify_text)
    def attr(self, selector=None, attr: str='', **kwargs):
        '''
        Extract an attribute of an HTML element.
        The **kwargs are the keyword arguments that can be added are from
        the BaseParser.modify_text method.
        '''
        selector = self._get_selector(selector)
        return partial(self._attr, selector=selector, attr=attr,
                       **kwargs)

    def _attr(self, url, data, selector=None, attr='', **kwargs):
        for element in self._select(url, data, selector):
            attr = element.attrib.get(attr)
            yield self._modify_text(attr, **kwargs)

    @add_other_doc(BaseParser._modify_text)
    def url(self, selector=None, **kwargs):
        selector = self._get_selector(selector)
        return partial(self._attr, selector=selector, attr='href',
                       **kwargs)

    def date(self, selector=None, fmt: str='YYYYmmdd', attr: str=None, index:
                 int=None):
        '''
        Returns a python date object with the specified format.
        '''
        selector = self._get_selector(selector)
        return partial(self._date, selector=selector,
                       fmt=fmt, attr=attr, index=index)

    def _date(self, url, data, selector=None, fmt='', attr=None, index=None):
        for element in self._select(url, data, selector):
            if attr:
                date = sel_attr(element, selector, attr=attr, index=index)
            else:
                date = sel_text(element, selector, index=index)
            if date:
                return datetime.strptime(date, fmt)

    def sel_raw_html(self, elements):
        return [el.raw_html for el in elements]

    def js_array(self, selector=None, var_name='', var_type=None):
        selector = self._get_selector(selector)
        return partial(self._js_array, selector=selector, var_name=var_name,
                       var_type=var_type)

    def _js_array(self, url, data, selector=None, var_name='', var_type=None):
        var_regex = 'var\s*'+var_name+'\s*=\s*(?:new Array\(|\[)(.*)(?:\)|\]);'
        for element in self._select(url, data, selector):
            array_string = list(self._modify_text(url, element.text, regex=var_regex))
            if array_string:
                if var_type:
                    yield list(map(var_type, array_string[0].split(',')))
                yield array_string[0].split(',')

    def fill_form(self, elements, fields={}, attrs=[]):
        from .sources import WebSource
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
    def _convert_data(self, url, data):
        xml = xmljson.badgerfish.etree(json.loads(data),
                                       root=etree.Element('root'))
        return xml

    def dict(self, selector=None):
        selector = self._get_selector(selector)
        return partial(self._dict, selector=selector)

    def _dict(self, data, selector=None):
        for element in self._select(selector, data):
            yield {child.tag: child.text for child in element.getchildren()}


class TextParser(BaseParser):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _convert_data(self, url, data):
        return data

    def _select(self, url, data, selector):
        data = self._convert_data(url, data)
        if selector:
            return data.split(selector)
        return data

    def _get_selector(self, selector):
        return selector


class CSVParser(BaseParser):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _convert_data(self, url, data):
        return data

    def _extract(self, data, selector):
        return [d.split(',') for d in data.split('\n') if d]

    def _select(self, url, data, selector):
        data = self._convert_data(url, data)
        if selector:
            return [data[selector]]
        return data

    def _get_selector(self, selector):
        return selector
