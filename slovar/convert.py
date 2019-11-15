import six
from urllib.parse import parse_qsl

from slovar.strings import split_strip, str2dt, str2rdt


def parametrize(func):

    def wrapper(dset, name, default=None, raise_on_values=None, pop=False,
                            allow_missing=False, set_as=None, pop_empty=False,
                            _raise=True, mod=None, **kw):

        if pop_empty:
            allow_missing = True

        if default is None:
            try:
                value = dset[name]
            except KeyError:
                if not allow_missing:
                    raise KeyError("Missing '%s'" % name)
                else:
                    return
        else:
            value = dset.get(name, default)

        if pop_empty and not value:
            dset.pop(name, None)
            return

        if raise_on_values and value in raise_on_values:
            raise ValueError("'%s' can not be any of %s" % (name, raise_on_values))

        try:
            result = func(dset, value, **kw)
        except Exception:
            if _raise:
                import sys
                raise ValueError(sys.exc_info()[1])
            else:
                return

        if mod:
            result = mod(result)

        if pop:
            dset.pop(name, None)
            if set_as:
                dset[set_as] = result
        else:
            dset[set_as or name] = result

        return result

    return wrapper


@parametrize
def asbool(dset, value):
    truthy = frozenset(('t', 'true', 'y', 'yes', 'on', '1'))
    falsey = frozenset(('f', 'false', 'n', 'no', 'off', '0'))

    if value is None:
        return False

    if isinstance(value, bool):
        return value

    lvalue = str(value).strip().lower()
    if lvalue in truthy:
        return True
    elif lvalue in falsey:
        return False
    else:
        raise ValueError(
                'Dont know how to convert `%s` to bool' % value)


@parametrize
def aslist(dset, value, sep=',', remove_empty=True, unique=False, itype=None):
    if isinstance(value, list):
        _lst = value
    elif isinstance(value, str):
        _lst = split_strip(value, sep, remove_empty)
    else:
        _lst = [value]

    if remove_empty:
        _lst = [it for it in _lst if it is not None]

    if unique:
        _lst = list(set(_lst))

    if itype:
        _lst = [itype(it) for it in _lst]

    return _lst


def asset(*args, **kw):
    return set(aslist(*args, **kw))


@parametrize
def asint(dset, value):
    return int(value)


@parametrize
def asfloat(dset, value):
    return float(value)


@parametrize
def asstr(dset, value):
    return str(value)


@parametrize
def asunicode(dset, value):
    return str(value)


@parametrize
def asrange(dset, value, typecast=str, sep='-'):
    if isinstance(value, list):
        list_ = value
    elif isinstance(value, str):
        rng = split_strip(value, sep)
        if len(rng) != 2:
            raise ValueError('bad range')
        list_ = list(range(int(rng[0]), int(rng[1])+1))

    else:
        list_ = [value]

    return [typecast(e) for e in list_]


def asdict(dset, name, _type=None, _set=False, pop=False):
    """
    Turn this 'a:2,b:blabla,c:True,a:'d' to {a:[2, 'd'], b:'blabla', c:True}

    """

    try:
        value = dset[name]
    except KeyError:
        raise KeyError("Missing '%s'" % name)

    if _type is None:
        _type = lambda t: t

    dict_str = dset.pop(name, None)
    if not dict_str:
        return {}

    _dict = {}
    for item in split_strip(dict_str):
        key, _, val = item.partition(':')
        if key in _dict:
            if type(_dict[key]) is list:
                _dict[key].append(val)
            else:
                _dict[key] = [_dict[key], val]
        else:
            _dict[key] = _type(val)

    if _set:
        dset[name] = _dict
    elif pop:
        dset.pop(name, None)

    return _dict


@parametrize
def asdt(dset, value):
    return str2dt(value)


def qs2dict(qs):
    from slovar import slovar
    return slovar(parse_qsl(qs, keep_blank_values=True))


@parametrize
def asqs(dset, value):
    return qs2dict(value)

from bson import ObjectId
@parametrize
def asdtob(dset, value):
    return str(ObjectId.from_datetime(str2dt(value)))
