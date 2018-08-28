import lxml.cssselect
from collections import OrderedDict
from lxml.etree import XPath
import attr
import types


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

def str_as_tuple(something):
    if something is not None:
        if type(something) in [list, dict, tuple] or \
                isinstance(something, types.GeneratorType):
            return something
        return (something,)


def wrap_list(something):
    if something and type(something) not in [list, tuple]:
        return [something]
    return something

class AttrDict(dict):
    def __iter__(self):
        for val in self.values():
            yield val

def attr_dict(attrs):
    if type(attrs) == AttrDict:
        return attrs
    attrs_dict = AttrDict()
    for attr_item in attrs:
        attrs_dict[attr_item.name] = attr_item
    return attrs_dict


# Decorator to copy docstrings from other functions
def add_other_doc(other_func):
    def _doc(func):
        if other_func.__doc__ and func.__doc__:
            func.__doc__ = func.__doc__ + other_func.__doc__
        else:
            func.__doc__ = other_func.__doc__
        return func
    return _doc


def depth(l):
    if isinstance(l, list):
        return 1 + max(depth(item) for item in l)
    else:
        return 0


def padd_list(reference, to_fill, fill_type):
    difference = len(reference) - len(to_fill)
    if difference:
        return [*to_fill, *[fill_type() for _ in range(difference)]]
    return to_fill
