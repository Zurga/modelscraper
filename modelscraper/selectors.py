import attr
from lxml.cssselect import CSSSelector
import re
from .helpers import str_as_tuple


#TODO fix the TextSelector
@attr.s
class TextSelector:
    selector = attr.ib(default=attr.Factory(list), convert=str_as_tuple)

    def __call__(self, data):
        selected = data
        for sel in self.selector:
            if type(sel) in (slice, int) and type(selected) in (list, tuple):
                selected = selected[sel]
            elif type(sel) is str:
                selected = selected.split(sel)


class JavaScriptVarSelector(object):
    def __init__(self, selector):
        assert type(selector) is str, 'only a string is allowed as selector'
        self.all_scripts = CSSSelector('script')
        self.var_name = selector
        self.var_regex = re.compile('''var\s*{}\s*=\s*([{{}}\[\]\s\n\r\:,\.\d\w'"\/\-\+\*\&%#<>!^\(\)\\\|\?^@]+);'''.format(selector)).findall

    def __call__(self, data):
        scripts = self.all_scripts(data)
        for script in scripts:
            for var in self.var_regex(script.text):
                return var


class ORCSSSelector(object):
    '''
    A subclass of the CSSSelector which allows for the
    grouping of multiple css selectors which will be applied
    in a fashion similar to an OR clause.
    '''

    def __init__(self, selectors):
        assert len(selectors) > 1 and type(selectors) in (list, tuple), \
            "please specify more than one selector and put them in a list or tuple"
        self.selectors = [CSSSelector(selector) for selector in selectors]

    def __call__(self, data):
        for selector in self.selectors:
            selected = selector(data)
            if selected:
                return selected


class SliceSelector(object):
    def __init__(self, selector=[]):
        self.selector = selector

    def __call__(self, data):
        if len(self.selector) == 1:
            return data[self.selector]
        if len(self.selector) == 2:
            return data[self.selector[0]:self.selector[1]]
        if len(self.selector) == 3:
            return data[self.selector[0]:self.selector[1]:
                        self.selector[2]]

