from datetime import datetime
import json
import re
import logging
from functools import partial
from urllib import parse as urlparse

import lxml.html as lxhtml
import lxml.etree as etree
from lxml.cssselect import CSSSelector
from cssselect import SelectorSyntaxError

from scrapely import Scraper
from jq import jq, _Program

from .helpers import add_other_doc, wrap_list, format_docstring
from .selectors import ORCSSSelector, JavascriptVarSelector


class BaseParser(object):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

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
                if not selected:
                    self.logger.warning(str(selector) + 'selected nothing' + str(url))
                    if debug:
                        print(etree.tostring(data))
                return selected
            return (data,)
        return []

    def _modify_text(self, text: str, replacers=None, substitute='', regex:
                     str='', numbers: bool=False, template: str='',
                     translation_table: dict={}):
        '''
        replacers : list of str, optional
                    Must be used with the substitute parameter.
                    For each key found in the replacers list,
                    the value found in the substitute list will be set
                    with the help of the str.replace function.

        substitute : list of str, optional
                    Must be used with the replacers parameter.
                    The value to be substituted for each replacement character
                    found in the replacers parameter

        regex : str, optional
                The regular expression provided here will be executed against
                the text. The regular expression is executed with a
                re.findall().  All the text which matched will be concatenated
                with ''.join().

        numbers : bool, optional
                  If set to True, only numbers found in the text will be
                  returned.

        template : str, optional
                   A template string that will be applied with the str.format
                   method to the text found.

        translation : dict, optional
                   This will execute the str.translation with translation_table
                   provided on the text found. :seealso:python.str.maketrans.

        Note
        ----
        Order of occurence for the methods used by setting each parameter:
            regex -> replacers -> translation -> numbers -> template.
        '''
        text = text.strip()
        if regex:
            regex = re.compile(regex)
            try:
                text = ''.join([found for found in regex.findall(text)])
            except:
                print('regex error', text)

        if replacers and substitute:
            for key, subsitute in zip(replacers, substitute):
                text = text.replace(key, substitute)

        if translation_table:
            text = text.translate(translation_table)

        if numbers and any(map(str.isdecimal, text)):
            text = int(''.join([c for c in text if c.isdecimal() and c]))

        if template:
            text = template.format(text)
        return text

    def text(self, selector=None, **kwargs):
        """
        Parameters
        ----------
        replacers: string or list of str
                   That have to be replaced in the text. Used in combination
                   with substitute.
        substitute: str
                   The substitute used in the replacers parameter.
        """
        selector = self._get_selector(selector)
        return partial(self._text, selector=selector, **kwargs)

    def _text(self, url, data, selector=None, index=None, **kwargs):
        '''
        Selects and modifies text.
        '''
        for element in self._select(url, data, selector):
            if element:
                stripped = str(element).lstrip().rstrip()
                yield self._modify_text(stripped, **kwargs)
            else:
                yield ''

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

    def custom_func(self, selector=None, function=None):
        selector = self._get_selector(selector)
        return partial(self._custom_func, selector=selector, function=function)

    def _custom_func(self, url, data, selector=None, function=None):
        for element in self._select(url, data, selector):
            yield function(element)


_HTMLParser_selector_doc = '''
            A string which represents a selector that can be used by
            this parser. It will be applied to the data to select the correct
            elements.  '''


class HTMLParser(BaseParser):
    '''
    A parser that is able to parse both XML and HTML.

    Attributes
    ----------
    selectors : (CSSSelector, ORCSSSelector, etree.XPath, JavascriptVarSelector)
                The type of selectors that can be used with this parsers
                "selectors" keyword argument. If a string is provided, this
                string will be converted into a CSSSelector or an XPath
                selector.
    '''
    _data_types = (lxhtml.HtmlElement, etree._Element, lxhtml.FormElement)
    _table_row_selector = ORCSSSelector('th', 'td')
    selectors = (CSSSelector, ORCSSSelector, etree.XPath,
                 JavascriptVarSelector)

    def __init__(self, parse_escaped: bool=True):
        '''
        Parameters
        ----------
        parse_escaped : bool, optional
                        If set to True, '&lt;' and '&gt;' will be converted to
                        '<' and '>' respectively.
        '''
        super().__init__()
        self.scrapely_parser = None
        self.parse_escaped = parse_escaped

    def _convert_data(self, url, data):
        if type(data) in self._data_types:
            return data
        else:
            if not data:
                return False
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
                self.logger.exception("Unable to convert" + url + str(data) +
                                      str(type(data)))
                return False

            urlparsed = urlparse.urlparse(url)
            data.make_links_absolute(urlparsed.scheme + '://' +
                                     urlparsed.netloc)
            return data

    def _get_selector(self, selector):
        if selector:
            if type(selector) in self.selectors:
                return selector
            else:
                assert type(selector) is str, \
                    "selector is not a string %r" % selector
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

    @format_docstring(selector_doc=_HTMLParser_selector_doc)
    @add_other_doc(BaseParser._modify_text)
    def text(self, selector: str=None, all_text: bool=True, **kwargs):
        ''' Selects the text found between the HTML tags.

        Parameters
        ----------
        selector : str, JavaScriptSelector, CSSOrSelector, optional
                   {selector_doc}

        all_text : bool, optional
                   If set to True, all text in child elements will be
                   selected too. Set it to False if only the text in the
                   selected element should be parsed.
        '''

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
        selector = self._get_selector(selector)
        return partial(self._table, selector=selector)

    def _table(self, url, data, selector=None):
        for element in self._select(url, data, selector):
            for row in element.cssselect('tr'):
                cells = row.cssselect('td')
                if cells:
                    yield [cell.text_content() for cell in cells]

    @add_other_doc(BaseParser._modify_text)
    def attr(self, selector=None, attr: str='', **kwargs):
        ''' Extract an attribute of an HTML element.

        Parameters
        ----------
        selector : str
                   A selector that can be used with this parser.

        attr : str
               The attribute to select from the element selected.
        '''
        selector = self._get_selector(selector)
        return partial(self._attr, selector=selector, attr=attr,
                       **kwargs)

    def _attr(self, url, data, selector=None, attr='', **kwargs):
        for element in self._select(url, data, selector):
            sel_attr = element.attrib.get(attr)
            if sel_attr:
                yield self._modify_text(sel_attr, **kwargs)

    @format_docstring(selector_doc=_HTMLParser_selector_doc)
    @add_other_doc(BaseParser._modify_text)
    def url(self, selector=None, **kwargs):
        '''
        Extracts the URL from the "href" attribute of the selected "a" tag.

        Parameters
        ----------
        selector : str, optional
                   {selector_doc}
        '''# .format(selector_doc=self._selector_doc)
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
                date = self.attr(element, selector, attr=attr, index=index)
            else:
                date = self.text(element, selector, index=index)
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


class JSONParser(BaseParser):
    '''
    A parser that will parse JSON data. The JSON is converted to XML with the
    xmljson package. This way, normal CSSSelectors, XPath selectors and the
    other selectors that can be used to select data from the JSON.

    .. xmljson

    '''
    name = 'JSONParser'
    _data_types = [list, dict]
    # _dialects = {key.lower(): val for key, val in sorted(vars(xmljson).items())
    #             if isinstance(val, type) and issubclass(val, xmljson.XMLData)}
    selectors = (_Program,)

    # @add_other_doc(HTMLParser.__init__, section='Parameters')
    def __init__(self, dialect='badgerfish', invalid_tags='drop', *args,
                 **kwargs):
        '''
        Parameters
        ----------
        dialect : str, optional
                  The dialect to use in the conversion from JSON to XML. See
                  the XMLJSON documentation for more information.

        invalid_tags : str, optional
                  Decide what to do with key that are valid in JSON but contain
                  characters that are invalid according to the XML standard.
                  The default is to drop these characters because the
                  lxml.etree parsers raises a ValueError when it finds these
                  invalid keys.
        '''
        super().__init__()
        # assert dialect in self._dialects, "Please use a supported dialect" + \
        #    str(self._dialects.keys())
        # .self.converter = self._dialects[dialect](invalid_tags=invalid_tags)

    def _convert_data(self, url, data):
        if data and type(data) in self._data_types:
            return data
        elif data:
            try:
                data = json.loads(data)
                return data
            except Exception as E:
                self.logger.exception(url + ' could not be loaded as json' +
                                      '\n' + str(data))
                return False
        else:
            self.logger.warning(url +
                                'returned no data, perhaps the selector is ' +
                                'not working...')
            return False

    def _get_selector(self, selector):
        if selector:
            if type(selector) in self.selectors:
                return selector
            else:
                assert type(selector) is str, "Selector must be str"
                try:
                    return jq(selector)
                except:
                    self.logger.exception(str(selector) + 'cannot compile')

    def _select(self, url, data, selector, debug=False):
        data = self._convert_data(url, data)
        if data:
            if selector:
                return selector.transform(data, multiple_output=True)
            return [data]
        return []

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
                self.logger.warning('Unable to convert data' + str(url))
                data = ''
        return data

    def _select(self, url, data, selector, debug=False):
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
            self.logger.warning('Unable to convert data.' + url + '\n' +
                                str(data))
            return False

    def _select(self, url, data, selector, debug=False):
        data = self._convert_data(url, data)
        if selector and data:
            return wrap_list(data[selector])
        return data

    def _get_selector(self, selector):
        return selector
