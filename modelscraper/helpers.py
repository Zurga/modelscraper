import lxml.cssselect
from collections import OrderedDict
from lxml.etree import XPath
import attr


#TODO move the selectors to a seperate folder and/or file
@attr.s
class SliceSelector:
    selector = attr.ib(default=attr.Factory(list))

    def __call__(self, data):
        if len(self.selector) == 1:
            return data[self.selector]
        if len(self.selector) == 2:
            return data[self.selector[0]:self.selector[1]]
        if len(self.selector) == 3:
            return data[self.selector[0]:self.selector[1]:
                        self.selector[2]]


def selector_converter(selector):
    '''
    Create a selector out of a string or number. If the input is a string,
    a CSS or XPath selector are created, if the input is a number or a
    tuple/list of numbers, the selector will be turned into a slice selector.

    Applies basic parsing ond the selector, allowing css query grouping.
    (\w+ > \w+) ~ \w+ will result in a sibling selection of the parent element in
    the left part of the parenthesized selector.
    '''
    parent_sibling = '\((.*)\s*>\s*(.*)\s*\)\s*~\s*(.*)'
    '''
    if re.match(parent_sibling, selector):
        parent, child, sibling = re.match(parent_sibling, selector).groups()
        selector = lambda x: [el.getparent().getnext() for el in css(parent+'>'+child)(x)]
        return selector
    '''
    if selector:
        if type(selector) == int:
            return SliceSelector((selector,))
        if type(selector) in (list, tuple):
            return SliceSelector(selector)
        if type(selector) == lxml.cssselect.CSSSelector:
            return selector
        try:
            return lxml.cssselect.CSSSelector(selector)
        except lxml.cssselect.SelectorSyntaxError:
            return XPath(selector)
        except:
            raise Exception('This value for a selector was not understood',
                            selector)

'''
def source_conv(source):
    if source:
        if source.__class__ == Source:
            return source
        return Source(**source) if type(source) == dict else Source()
'''


def func_conv(func_list):
    assert type(func_list) == list or str, "Function list should be " \
        "a list or a string containing comma seperated function names."
    if type(func_list) == list:
        return func_list
    return [func_list]


def attr_dict(attrs):
    if type(attrs) == OrderedDict:
        return attrs
    attrs_dict = OrderedDict()
    for attr_item in attrs:
        attrs_dict[attr_item.name] = attr_item
    return attrs_dict
