import types

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

def add_other_doc(other_func):
    '''
    Decorator method which will copy documentation from one method into another.
    '''
    def _doc(func):
        if other_func.__doc__ and func.__doc__:
            func.__doc__ = func.__doc__ + other_func.__doc__
        else:
            func.__doc__ = other_func.__doc__
        return func
    return _doc

def get_name(instance):
    print(instance)
    for name, var in globals().items():
        if var is instance:
            return name
