import types
from numpydoc.docscrape import NumpyDocString


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


def extract_section(obj, section):
    docstr = NumpyDocString(obj.__doc__)
    section = section.lower().capitalize()
    if section in ('Parameters', 'Returns', 'Yields', 'Other Parameters',
                   'Raises', 'Warns'):
        return docstr[section]
    return []


def get_next(iterator, index=0):
    if isinstance(iterator, list):
        try:
            return iterator.pop(index)
        except IndexError:
            return False
    elif isinstance(iterator, types.GeneratorType):
        try:
            return next(iterator)
        except StopIteration:
            return False
    else:
        return iterator


def add_other_doc(other_func, section=''):
    '''
    Decorator method which will copy documentation from one method into
    another.
    '''
    def _doc(func):
        if other_func.__doc__ and func.__doc__:
            if section:
                other_function_doc = extract_section(other_func, section)
                function_doc = NumpyDocString(func.__doc__)
                function_doc[section].extend(other_function_doc)
                func.__doc__ = str(function_doc).strip()
            else:
                func.__doc__ = func.__doc__ + other_func.__doc__

        else:
            func.__doc__ = other_func.__doc__

        return func
    return _doc


def format_docstring(**kwargs):
    def _format_doc(func):
        if func.__doc__:
            func.__doc__ = func.__doc__.format(**kwargs)
        return func
    return _format_doc


def get_name(instance):
    for name, var in globals().items():
        if var is instance:
            return name


def read_zip_file(zipfile):
    content = ''
    with ZipFile(BytesIO(zipfile)) as myzip:
        for file_ in myzip.namelist():
            with myzip.open(file_) as fle:
                content += fle.read().decode('utf8')
    return content
