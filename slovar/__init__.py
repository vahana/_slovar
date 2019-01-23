import re
import logging
import collections
import logging
from bson import ObjectId

from slovar import convert
from slovar.dictionaries import *
from slovar.json import json_dumps
from slovar.lists import *
from slovar.strings import *

def parse_func_params(s):
    pattern = r'(\w[\w\d_]*)\((.*)\)$'
    match = re.match(pattern, s)
    if match:
        return list(match.groups())
    else:
        return []

TCAST_NONE = True
log = logging.getLogger(__name__)


class slovar(dict):
    """Named dict, with some set functionalities

        dset = slovar(a=1,b={'c':1})
        dset.a == dset['a'] == 1
        dset.b.c == 1
        dset.subset(['a']) == {'a':1} == dset.subset('-b')

    """
    # Note: We use self.__class__ to return new instances of subclasses
    # instead of slovar when necessary

    @classmethod
    def to_dicts(cls, iterable, fields):
        return [e.extract(fields) for e in iterable]

    @classmethod
    def from_dotted(cls, dotkey, val):
        # 'a.b.c', 100 -> {a:{b:{c:100}}}
        # 'a.b.1', 100 -> {a:{b:[None,100]}}

        key, _, sufix = dotkey.partition('.')

        if not sufix:
            if key.isdigit():
                _lst = [None]*int(key) + [val]
                return _lst
            else:
                return cls({key:val})

        if key.isdigit():
            _lst = [None]*int(key) + [cls.from_dotted(sufix, val)]
            return _lst
        else:
            return cls({key: cls.from_dotted(sufix, val)})

    def __init__(self, *arg, **kw):
        super(slovar, self).__init__(*arg, **kw)
        self.to_slovar()

    def bad_value_error_klass(self, e):
        return ValueError(e)

    def missing_key_error_klass(self, e):
        return AttributeError(e)

    def __getattr__(self, key):
        if key.startswith('__'):
            raise AttributeError('Attribute error %s' % key)
        try:
            return self[key]
        except KeyError as e:
            raise self.missing_key_error_klass(e.args)

    def __setattr__(self, key, val):
        if key.startswith('__'):
            return super().__setattr__(key,val)

        #this makes a.b.c access work for nested slovars
        if isinstance(val, dict) and not isinstance(val, self.__class__):
            val = self.__class__(val)
        self[key] = val

    def __delattr__(self, key):
        self.pop(key, None)

    def __contains__(self, item):
        if isinstance(item, (tuple, list, set)):
            return bool(set(self.keys()) & set(item))
        else:
            return super(slovar, self).__contains__(item)

    def __add__(self, item):
        return self.copy().update(item)

    def __iadd__(self, item):
        return self.update(item)

    def __getitem__(self, key):
        return super(slovar, self).__getitem__(key)

    def to_dict(self, fields=None):
        return self.extract(fields)

    def to_dict_type(self):
        return super(slovar, self).copy()

    def to_slovar(self):
        for key, val in list(self.items()):
            if isinstance(val, dict):
                self[key] = slovar(val)
            if isinstance(val, list):
                new_list = []
                for each in val:
                    if isinstance(each, dict):
                        new_list.append(slovar(each))
                    else:
                        new_list.append(each)
                self[key] = new_list

        return self

    def copy(self):
        return self.__class__(super(slovar, self).copy())

    def extract(self, fields, defaults=None):
        if not fields:
            return self

        fields, only, exclude, nested, show_as, show_as_r, trans, assignments, star, flats, envelope =\
                process_fields(fields).mget(['fields','only','exclude', 'nested',
                                            'show_as', 'show_as_r', 'transforms', 'assignments',
                                            'star', 'flats', 'envelope'])

        nested_keys = list(nested.keys())

        def process_lists(flat_d):
            for nkey, nval in list(nested.items()):
                if '..' in nkey:
                    pref, suf = nkey.split('..', 1)
                    _lst = []

                    for ix in range(len(_d.get(nval, []))):
                        kk = '%s.%s.%s'%(pref,ix,suf)
                        _lst.append(flat_d.get(kk))
                        ix+=1

                    new_key = show_as.get(nkey,'%s.%s'%(pref,suf))
                    nested_keys.append(new_key)
                    flat_d[new_key] = _lst

        if star:
            _d = self
        else:
            _d = self.subset(only + ['-'+e for e in exclude])

        if nested:
            flat_d = self.flat(keep_lists=0)
            process_lists(flat_d)
            flat_d = flat_d.subset(nested_keys)
            _d = _d.remove(list(nested.values())).update(flat_d)

        for new_key, key in list(show_as_r.items()):
            if key in _d:
                #reverse merge to keep all show_as values and merge the rest
                _d = self.__class__({new_key:_d.get(key)}).merge(_d)

        if not star: # if no star then dont keep the "original" keys
            #remove original keys
            for _k in list(show_as_r.values()):
                if _k not in fields: # if key in the original fields, dont pop it. e.g. `a__as__x.a,a`
                    _d.pop(_k, None)

        def tcast(_dict, key, trs, default_value=None):
            val = _dict.get(key, default_value)

            if val is None and not TCAST_NONE:
                log.debug('extracted key %r is None' % key)
                return val

            safe = False

            # if isinstance(val, list):
            #     for tr in trs:
            #         parsed_trs = parse_func_params(tr)
            #         op = parsed_trs[0]
            #         args = parsed_trs[1:]
            #         arg = None

            #         if args:
            #             arg = args[0]

            #         if op == 'sort':
            #             sort_func = None
            #             reverse = False

            #             if arg:
            #                 if arg[0] in ['-', '+']:
            #                     sort_direction = arg[0]
            #                     arg = arg[1:]

            #                 sort_func = lambda x: x[arg]

            #             val = sorted(val, key=sort_func, reverse=sort_direction=='-')

            #         elif op == 'size' and arg:
            #             val = val[:int(arg)]

            #         elif op == 'concat':
            #             sep = arg or ','
            #             val = sep.join(val)

            #     return val

            def concat(val):
                if isinstance(val, list):
                    return ''.join(val)
                else:
                    return str(val)

            for tr in trs:
                try:
                    if 'safe' in tr:
                        safe = True
                    elif tr in ('str', 'unicode'):
                        val = str(val)
                    elif tr == 'int':
                        val = int(val) if val else val
                    elif tr == 'float':
                        val = float(val) if val else val
                    elif tr == 'flat' and isinstance(val, slovar):
                        val = val.flat()
                    elif tr == 'dt':
                        if val:
                            val = str2dt(val)
                    elif tr == 'dtob':
                        if val:
                            val = ObjectId(val).generation_time
                    elif tr == 'concat':
                        val = concat(val)
                    else:
                        _type = type(val)
                        try:
                            method = getattr(_type, tr)
                            if not isinstance(method, collections.Callable):
                                raise self.bad_value_error_klass('`%s` is not a callable for type `%s`' % (tr, _type))
                            val = method(val)
                        except AttributeError as e:
                            raise self.bad_value_error_klass('type `%s` does not have a method `%s`' % (_type, tr))

                except:
                    import sys
                    log.error('typecast failed for key=`%s`, value=`%s`: %s' %
                                                (key, _d[key], sys.exc_info()[1]))

                    if not safe:
                        raise

            return val

        for key, trs in list(trans.items()):
            if key in _d:
                _d[key] = tcast(_d, key, trs)

        for kk, vv in assignments.items():
            val, _, tr = vv.partition(':')
            trs = split_strip(tr, '|')
            _d[kk] = tcast(_d, kk, trs, val) if trs else val

        if defaults:
            _d = _d.flat().merge_with(slovar(defaults).flat())

        if envelope:
            _d = slovar({envelope:_d})

        return _d.unflat()

    def get_by_prefix(self, prefix):
        if not isinstance(prefix, list):
            prefixes = [prefix]
        else:
            prefixes = prefix

        _d = self.__class__()
        for k, v in list(self.items()):
            for pref in prefixes:
                _pref = pref[:-1]

                if pref.endswith('*'):
                    if k.startswith(_pref):
                        ix = _pref.rfind('.')
                        if ix > 0:
                            _pref = _pref[:ix]
                            k = k[len(_pref)+1:]
                        _d[k] = v
                else:
                    if k == pref:
                        ix = _pref.rfind('.')
                        if ix > 0:
                            _pref = _pref[:ix]
                            k = k[len(_pref)+1:]

                        _d[k]=v

        return _d.unflat()

    def subset(self, keys, defaults=None):

        if keys is None:
            return self

        only, exclude = process_fields(
            keys, parse=False
        ).mget(['only','exclude'])

        _d = self.__class__()

        if only and exclude:
            raise self.bad_value_error_klass(
                'Can only supply either positive or negative keys,'
                ' but not both'
            )

        if only:
            prefixed = [it for it in only if it.endswith('*')]
            exact = [it for it in only if not it.endswith('*')]

            if exact:
                _d = self.__class__(
                    [[k, v] for (k, v) in list(self.items()) if k in exact]
                )

            if prefixed:
                _d = _d.update_with(self.get_by_prefix(prefixed))

        elif exclude:
            _d = self.__class__([[k, v] for (k, v) in list(self.items())
                          if k not in exclude])

        if defaults:
            _d = _d.flat().merge_with(slovar(defaults).flat()).unflat()

        return _d

    def remove(self, keys, flat=False):
        if isinstance(keys, str):
            keys = [keys]

        _self = self.flat() if flat else self.copy()

        for k in keys:
            _self.pop(k, None)
        return _self.unflat() if flat else _self

    def update(self, d_):
        super(slovar, self).update(self.__class__(d_))
        return self

    def merge(self, d_):
        merge(self, d_)
        return self

    def pop_by_values(self, vals):
        if not isinstance(vals, list):
            vals = [vals]

        for k, v in list(self.items()):
            if v in vals:
                self.pop(k)
        return self

    def get_tree(self, prefix, defaults={}, sep='.'):
        if prefix[-1] != '.':
            prefix += sep

        _dict = self.__class__(defaults)
        for key, val in list(self.items()):
            if key.startswith(prefix):
                _k = key.partition(prefix)[-1]
                _dict[_k] = val
        return _dict

    def mget(self, keys):
        return [self[e] for e in split_strip(keys) if e in self]

    def has(self, keys, check_type=str,
            err='', _all=True, allow_missing=False,
            allowed_values=[]):
        errors = []

        if isinstance(keys, str):
            keys = [keys]

        self_flat = self.flat().update(self) # update with self to include high level keys too

        def missing_key_error(_type, key):
            if _type == dict:
                missing = ['%s.%s' % (key, val) for val in allowed_values]
            else:
                missing = allowed_values

            return 'Missing key or invalid values for `%s`. Allowed values are: `%s`'\
                                          % (key, missing)

        def error_msg(msg):
            if "%s" in err:
                error = err % msg
            elif err:
                error = err
            else:
                error = msg

            errors.append(error)
            return error

        for key in keys:
            if key in self_flat:
                if check_type and not isinstance(self_flat[key], check_type):
                    error_msg('`%s` must be type `%s`, got `%s` instead'\
                                          % (key, check_type.__name__,
                                             type(self_flat[key]).__name__))

                if allowed_values and self_flat[key] not in allowed_values:
                    error_msg(missing_key_error(check_type, key))

            elif not allow_missing:
                if allowed_values:
                    error_msg(missing_key_error(check_type, key))
                else:
                    error_msg('Missing key: `%s`' % key)

        if (errors and _all) or (not _all and len(errors) >= len(keys)):
            raise self.bad_value_error_klass('.'.join(errors))

        return True

    def transform(self, rules):
        _d = self.__class__()
        flat_dict = self.flat()

        for path, val in list(flat_dict.items()):
            if path in rules:
                _d.merge(slovar.from_dotted(rules[path], val))

        return _d

    def flat_keys(self, keys, keep_lists=True):
        self_copy = self.copy()
        for key in keys:
            val = self_copy.extract(key)
            if val and isinstance(val, dict):
                self_copy.pop(key, None)
                self_copy.update(val.flat(keep_lists=keep_lists))

        return self_copy

    def flat(self, keys=[], keep_lists=True):
        if keys:
            return self.flat_keys(keys, keep_lists=keep_lists)

        return self.__class__(flat(self, keep_lists=keep_lists))

    def unflat(self):
        return self.__class__(unflat(self))

    def set_default(self, name, val):
        cls = self.__class__
        if name not in self.flat():
            self.merge(cls.from_dotted(name, val))
        return val

    def with_defaults(self, **defaults):
        return self.update_with(defaults, overwrite=False)

    def fget(self, key, *arg, **kw):
        return self.flat().get(key, *arg, **kw)

    def update_with(self, _dict, overwrite=True, append_to=None,
                    append_to_set=None, flatten=None):

        def process_append_to_param(_lst):
            if isinstance(_lst, str):
                _lst = [_lst]

            if not _lst:
                return {}

            _d = {}
            for each in (_lst or []):
                k,_,sk = each.partition(':')
                _d[k]=sk

            return _d

        append_to = process_append_to_param(append_to)
        append_to_set = process_append_to_param(append_to_set)
        self_dict = self.copy()

        def _build_list(_lst, new_val):
            if isinstance(_lst, list):
                if isinstance(new_val, list):
                    _lst.extend(new_val)
                else:
                    _lst.append(new_val)
            else:
                raise self.bad_value_error_klass('`%s` is not a list' % key)

            return _lst

        def _append_to(self_dict, key, val):
            _lst = _build_list(self_dict.get(key, []), val)
            sort_key = append_to.get(key)
            sort_method = None
            reverse = False

            if sort_key:
                if sort_key.startswith('-'):
                    sort_key = sort_key[1:]
                    reverse = True
                elif sort_key.startswith('+'):
                    sort_key = sort_key[1:]

                if sort_key:
                    sort_method = lambda x: x.get(sort_key)

                _lst = sorted(_lst, key=sort_method, reverse=reverse)

            return _lst

        def _append_to_set(self_dict, key, val):
            new_lst = _build_list(self_dict.get(key, []), val)
            set_key = append_to_set.get(key)

            if set_key.startswith('-'):
                reverse_order = True
                set_key = set_key[1:]
            else:
                reverse_order = False

            #ie append_to_set=people:full_name. `full_name` is a set_key
            #this will mean make people unique for inner field `full_name`
            if set_key:
                _uniques = []
                _met = []
                _not_found = []

                #reverse the list so new values overwrite old ones,
                #since it was appended at the end
                for each in reversed(new_lst):
                    if set_key not in each:
                        _not_found.append(each)
                        continue

                    if each[set_key] in _met:
                        continue

                    _met.append(each[set_key])
                    _uniques.append(each)

                new_lst = sorted(_uniques, key= lambda x: x.get(set_key), reverse=reverse_order)
                new_lst.extend(_not_found)
            else:
                try:
                    new_lst = list(set(new_lst))
                except TypeError as e:
                    raise self.bad_value_error_klass('items in `%s` list not hashable. missed the set_key ?'\
                                     % (key))

            return new_lst

        if flatten:
            flat_keys = flatten if isinstance(flatten, list) else None
            self_dict = self_dict.flat(keys=flat_keys)
            _dict = _dict.flat(keys=flat_keys)

        for key, val in list(_dict.items()):
            if key in append_to:
                self_dict[key] = _append_to(self_dict, key, val)
            elif key in append_to_set:
                self_dict[key] = _append_to_set(self_dict, key, val)
            elif key not in self_dict:
                self_dict[key] = val
            elif overwrite:
                if (isinstance(overwrite, bool) and overwrite is True) or \
                                    (isinstance(overwrite, list) and key in overwrite):
                    self_dict[key] = val


        if flatten:
            self_dict = self_dict.unflat()

        return self_dict

    def merge_with(self, _dict):
        return self.update_with(_dict, overwrite=False)

    def contains(self, other, exclude=None):
        other_ = other.subset(exclude)
        return not other_ or self.subset(list(other_.keys())) == other_

    def pop_many(self, keys):
        poped = self.__class__()
        for key in keys:
            poped[key] = self.pop(key, None)
        return poped

    def any_key(self, keys):
        if not keys:
            return False
        return any(name in self for name in keys)

    def all_keys(self, keys):
        if not keys:
            return False
        return all(name in self for name in keys)

    def diff(self, sl2, diff_fields=[], flat_keys=[]):

        _self = self

        if flat_keys:
            _self = _self.flat(keys=flat_keys)
            sl2 = sl2.flat(keys=flat_keys)

        self_diff = slovar()
        sl2_diff = slovar()
        _diff = slovar()

        for kk in (diff_fields or list(_self.keys())):
            selfv = _self.get(kk, None)
            sl2v = sl2.get(kk, None)

            if selfv != sl2v:
                _diff[kk] = {'from': selfv, 'to': sl2v}
                self_diff[kk] = selfv
                sl2_diff[kk] = sl2v

        if not diff_fields:
            #iterate through missing keys in _self
            for kk in set(sl2.keys())-set(_self.keys()):
                _diff[kk] = {'from': None, 'to': sl2[kk]}
                self_diff[kk] = None
                sl2_diff[kk] = sl2[kk]

        return self_diff, sl2_diff

    def call_converter(self, name, *arg, **kw):
        try:
            return getattr(convert, name)(self, *arg, **kw)
        except KeyError as e:
            raise self.missing_key_error_klass(e)
        except ValueError as e:
            raise self.bad_value_error_klass(e)

    def asbool(self, *arg, **kw):
        return self.call_converter('asbool', *arg, **kw)

    def aslist(self, *arg, **kw):
        return self.call_converter('aslist', *arg, **kw)

    def asset(self, *arg, **kw):
        return self.call_converter('asset', *arg, **kw)

    def asint(self, *arg, **kw):
        return self.call_converter('asint', *arg, **kw)

    def asfloat(self, *arg, **kw):
        return self.call_converter('asfloat', *arg, **kw)

    def asdict(self, *arg, **kw):
        return self.call_converter('asdict', *arg, **kw)

    def asdt(self, *arg, **kw):
        return self.call_converter('asdt', *arg, **kw)

    def asstr(self, *arg, **kw):
        return self.call_converter('asstr', *arg, **kw)
        return asstr(self, *arg, **kw)

    def asrange(self, *arg, **kw):
        return self.call_converter('asrange', *arg, **kw)

    def asqs(self, *arg, **kw):
        return self.call_converter('asqs', *arg, **kw)

    def asdtob(self, *arg, **kw):
        return self.call_converter('asdtob', *arg, **kw)

    def json(self):
        return json_dumps(self)
