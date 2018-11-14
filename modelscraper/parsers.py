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
import lxml
from lxml.cssselect import CSSSelector
from cssselect import SelectorSyntaxError

from scrapely import Scraper
import xmljson

from .helpers import str_as_tuple, add_other_doc, wrap_list
from .selectors import ORCSSSelector, JavascriptVarSelector


logger = logging.getLogger(__name__)
print(xmljson.__version__)


class BaseParser(object):
    def _convert_data(self, source):
        raise NotImplementedError()

    def select(self, selector=None, debug=False):
        selector = self._get_selector(selector)
        return partial(self._select, selector=selector, debug=debug)

    def _select(self, url, data, selector=None, debug=False):
        data = self._convert_data(url, data)
        if data is not False:
            if selector:
                selected = selector(data)
                if debug:
                    print(selected)
                return selected
            return (data,)
        return []

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
            yield self._modify_text(stripped, **kwargs)

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
                else:
                    yield False


class HTMLParser(BaseParser):
    '''
    A parser that is able to parse both XML and HTML.
    '''

    data_types = (lxhtml.HtmlElement, etree._Element, lxhtml.FormElement)
    _table_row_selector = ORCSSSelector('th', 'td')
    selectors = (CSSSelector, ORCSSSelector, etree.XPath, JavascriptVarSelector)
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
                    return False

            except TypeError as e:
                return False

            except etree.XMLSyntaxError:
                return False

            except Exception as e:
                logging.log(logging.WARNING, str(self) + ': Unable to use data '+
                            'returned by URL:' + url +'\nException is: '+ str(e))
                return False

            urlparsed = urlparse.urlparse(url)
            data.make_links_absolute(urlparsed.scheme + '://' + urlparsed.netloc)
            return data

    def _get_selector(self, selector):
        if selector:
            if type(selector) in self.selectors:
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

    def _fallback(self, model, html, source):
        if not self.scrapely_parser:
            self.scrapely_parser = Scraper()

        html = self.scrapely_parser.HtmlPage(body=html)
        db_objct = self.db.read(uri, objct)
        if not db_objct:
            data = db_objct.attrs_to_dict()

            self.scrapely_parser.train_from_htmlpage(html, data)
            attr_dicts = self.scrapely_parser.scrape_page(html)

            for attr_dict in attr_dicts:
                objct = model._replicate(name=model.name, url=source.url)
                # Add the parsed values.
                objct.attrs_from_dict(attr_dict)
                yield objct
        return []

    def custom_func(self, selector=None, function=None):
        selector = self._get_selector(selector)
        return partial(self._custom_func, selector=selector, function=function)

    def _custom_func(self, url, data, selector=None, function=None):
        for element in self._select(url, data, selector):
            yield function(element)

    @add_other_doc(BaseParser._text)
    def text(self, selector=None, all_text=True, **kwargs):
        selector = self._get_selector(selector)
        return partial(self._text, selector=selector, all_text=True, **kwargs)

    def _text(self, url, data, selector=None, all_text=True, **kwargs):
        for element in self._select(url, data, selector):
            if type(element) in (lxhtml.HtmlElement, lxhtml.FormElement):
                if all_text:
                    text = element.text_content()
                else:
                    text = element.text
            elif type(element) == etree._Element:
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
            for row in element.cssselect('tr'):
                yield [cell.text_content() for cell in row.cssselect('td')]

    #@add_other_doc(BaseParser._modify_text)
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
        elements = self._select(url, data, selector)
        for element in self._select(url, data, selector):
            sel_attr = element.attrib.get(attr)
            yield self._modify_text(sel_attr, **kwargs)

    #@add_other_doc(BaseParser._modify_text)
    def url(self, selector=None, **kwargs):
        selector = self._get_selector(selector)
        return partial(self._attr, selector=selector, attr='href', **kwargs)

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
                yield datetime.strptime(date, fmt)

    def raw_html(self, selector=None, link_replacer=''):
        selector = self._get_selector(selector)
        return partial(self._raw_html, selector=selector,
                       link_replacer=link_replacer)

    def _raw_html(self, url, data, selector=None, link_replacer=''):
        for element in self._select(url, data, selector):
            yield self._modify_text(lxhtml.tostring(element))

    def js_array(self, selector=None, var_name='', var_type=None):
        selector = self._get_selector(selector)
        return partial(self._js_array, selector=selector, var_name=var_name,
                       var_type=var_type)

    def _js_array(self, url, data, selector=None, var_name='', var_type=None):
        var_regex = 'var\s*'+var_name+'\s*=\s*(?:new Array\(|\[)(.*)(?:\)|\]);'
        for element in self._select(url, data, selector):
            array_string = list(self._modify_text(element.text, regex=var_regex))
            if array_string:
                if var_type:
                    yield list(map(var_type, array_string[0].split(',')))
                yield array_string[0].split(',')
            else:
                yield False

    def pagination(self, selector=None, per_page=10, url_template='{}', debug=False):
        selector = self._get_selector(selector)
        return partial(self._pagination, selector=selector,
                       per_page=per_page, url_template=url_template,
                       debug=debug)

    def _pagination(self, url, data, selector=None, per_page=None,
                    url_template=None, debug=False):
        elements = list(self._select(url, data, selector))
        if elements:
            num_results = self._modify_text(elements[0].text, numbers=True)
            for i in range(1, int(int(num_results) / per_page)):
                formatted = url_template.format(i)
                if debug:
                    print(formatted)
                yield formatted
        else:
            yield False

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
    name = 'JSONParser'
    def _convert_data(self, url, data):
        if type(data) in self.data_types:
            return data
        else:
            try:
                loaded_json = json.loads(data)
            except Exception as E:
                logger.log(logging.WARNING, self.name + ' data from ' + url +
                           ' could not be loaded as json')
                return False
            xml = xmljson.badgerfish.etree(loaded_json,
                                           root=etree.Element('root'),
                                           drop_invalid_tags=True)
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
        if type(data) != str:
            try:
                data = str(data)
            except Exception as E:
                loggin.log(logging.WARNING, str(self) +
                           ':Unable to convert data for this url ' + str(url))
                data = ''
        return data

    def _select(self, url, data, selector):
        data = self._convert_data(url, data)
        if data:
            if selector:
                return data.split(selector)
            return [data]
        return []

    def _get_selector(self, selector):
        return selector


class CSVParser(BaseParser):
    data_types = (list, tuple)
    def __init__(self, delimiter=',', **kwargs):
        super().__init__(**kwargs)
        self.delimiter = delimiter

    def _convert_data(self, url, data):
        if type(data) in self.data_types:
            return data
        elif type(data) == str:
            return [d.split(',') for d in data.split('\n') if d]
        else:
            logging.log(WARNING, str(self) + ': The data returned is not csv' +
                        ' url:'+ url)
            return False

    def _select(self, url, data, selector):
        data = self._convert_data(url, data)
        if selector and data:
            return wrap_list(data[selector])
        return data

    def _get_selector(self, selector):
        return selector
