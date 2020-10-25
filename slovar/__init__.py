import re
import logging
import collections
import logging
import builtins
import copy
from bson import ObjectId
from datetime import datetime

from slovar import convert
from slovar.dictionaries import *
from slovar.json import json_dumps
from slovar.lists import *
from slovar.strings import *


def ld2l(ld, key):
    return [it[key] for it in ld]


def ld2dl(ld, key=None):
    dl = {}
    for _d in ld:
        for kk,vv in _d.items():
            if kk in dl:
                dl[kk].append(vv)
            else:
                dl[kk] = [vv]
    return dl


def parse_func_params(s):
    pattern = r'(\w[\w\d_]*)\((.*)\)$'
    match = re.match(pattern, s)
    if match:
        return list(match.groups())
    else:
        return []

TCAST_NONE = True
TCAST_FUNCS = ['sort', 'index', 'concat', 'slice', 'ld2l', 'split']

log = logging.getLogger(__name__)


class slovar(dict):
    """Named dict, with some set functionalities
    """

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
        super().__init__(*arg, **kw)

        #recursively convert dicts to slovar if they arent already
        for key, val in self.items():
            if isinstance(val, slovar):
                continue
            elif isinstance(val, dict):
                self[key] = slovar(val)
            elif isinstance(val, list):
                new_list = []
                for each in val:
                    if isinstance(each, dict) and not isinstance(each, slovar):
                        new_list.append(slovar(each))
                    else:
                        new_list.append(each)
                self[key] = new_list

    def __call__(self, key):
        return self.extract(key)

    def bad_value_error_klass(self, e):
        return ValueError(e)

    def missing_key_error_klass(self, e):
        return KeyError(e)

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
        if isinstance(val, dict) and not isinstance(val, slovar):
            val = slovar(val)
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

    @classmethod
    def to(cls, dct):
        if isinstance(dct, slovar):
            return dct.copy()

        return slovar(dct)

    def copy(self):
        return copy.deepcopy(self)

    def deepcopy(self):
        return copy.deepcopy(self)

    def tcast(self, key, val, trs):

        if val is None and not TCAST_NONE:
            log.debug('extracted key %r is None' % key)
            return val

        prev_tr = None

        def concat(val, sep=''):
            SEP = slovar(
                COMMA=',',
                SPACE=' ',
            )

            sep = SEP.get(sep, sep)

            if isinstance(val, list):
                return sep.join([str(it) for it in val if it])
            else:
                return str(val)

        for tr in trs:
            try:
                if 'safe' == tr or 'safe_none' == tr:
                    continue

                elif tr in ('str', 'unicode'):
                    val = str(val)

                elif tr == 'int':
                    val = int(val) if val else val

                elif tr == 'float':
                    val = float(val) if val else val

                elif tr == 'bool':
                    val = bool(val) if val else val

                elif tr == 'flat' and isinstance(val, slovar):
                    val = val.flat()

                elif tr == 'flatall' and isinstance(val, slovar):
                    val = val.flat(keep_lists=False)

                elif tr == 'unflat' and isinstance(val, slovar):
                    val = val.unflat()

                elif tr == 'dt':
                    if val:
                        val = str2dt(val)

                elif tr == 'tm2dt':
                    if val:
                        val = datetime.utcfromtimestamp(val/1000).strftime('%Y-%m-%d %H:%M:%S')

                elif tr == 'dtob':
                    if val:
                        val = ObjectId(val).generation_time

                elif tr == 'strip':
                    if isinstance(val, str):
                        val = val.strip()

                # elif tr == 'ld2dl' and isinstance(val, list):
                #     val = ld2dl(val)

                elif tr in TCAST_FUNCS:
                    prev_tr = tr

                elif prev_tr:
                    if prev_tr == 'sort':
                        reverse = False
                        if tr[0] in ['-', '+']:
                            reverse = tr[0] == '-'
                            tr = tr[1:]
                        val = sort_list(val, tr, reverse = reverse)

                    elif prev_tr == 'index':
                        val = val[int(tr)]

                    elif prev_tr == 'concat':
                        val = concat(val, tr or '')

                    elif prev_tr == 'slice':
                        val = val[:int(tr)]

                    elif prev_tr == 'ld2l':
                        val = ld2l(val, tr)

                    elif prev_tr == 'split':
                        if isinstance(val, str):
                            val = val.split(tr)

                    prev_tr = None

                elif tr.startswith('@'):
                    tr = tr[1:]
                    val = getattr(builtins, tr)(val)

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
                msg = 'typecast failed for key=`%s`, value=`%s`: %s' % (key, val, sys.exc_info()[1])
                log.error(msg)

                if 'safe' in trs:
                    return val
                elif 'safe_none' in trs:
                    return None
                else:
                    raise self.bad_value_error_klass(msg)

        return val

    def extract(self, fields, defaults=None):

        if not fields:
            return self

        op = process_fields(fields)

        def process_assignments(_d):
            for kk, vv in op.assignments.items():
                op.transforms.pop(kk, None)

                val, _, tr = vv.partition(':')

                if val == '__NOW__':
                    val = datetime.utcnow()
                elif val == '__TODAY__':
                    val = datetime.today()
                elif val == '__OID__':
                    val = str(ObjectId())
                elif val == '__NULL__':
                    val = {}

                if '..' in kk:
                    list_key, new_key = kk.split('..')
                    new_val = []

                    for it in _d[list_key]:
                        if tr:
                            val = self.tcast(list_key, val, split_strip(tr, '|'))

                        new_val.append(it.update({new_key:val}))

                    if new_val:
                        _d[list_key] = new_val

                else:
                    trs = split_strip(tr, '|')
                    if 'default' in trs:
                        trs.remove('default')
                        if kk in _d:
                            continue

                    _d[kk] = self.tcast(kk, val, trs) if trs else val

            return _d

        def process_show_as(_d):
            if not op.show_as_r:
                return _d

            _d_show_as = slovar()

            for new_key, key in list(op.show_as_r.items()):
                try:
                    _d_show_as[new_key] = _d.nested_get(key)
                except (KeyError,IndexError):
                    pass

            _d_remainder = slovar()
            for kk, count in collections.Counter(op.exp_only).items():
                if kk in op.show_as:
                    if len(op.show_as[kk]) == count:
                        if op.star:
                            _d = _d.nested_pop(kk)
                        continue

                if not op.star:
                    _d_remainder = _d_remainder.update_with(_d.subset(kk), flatten=kk)

            _d_show_as.update(_d_remainder)

            if op.star:
                return _d_show_as.merge(_d)

            return _d_show_as

        def process_trans(_d):
            for key, trs in list(op.transforms.items()):
                if key in _d:
                    _d[key] = self.tcast(key, _d.get(key), trs)
            return _d

        def process_flats(_d):
            for fld, keep in op.flats.items():
                _d = _d.flat([fld], keep_lists=keep)

            return _d

        def process_unflats(_d):
            if op.unflats:
                _d = _d.unflat(op.unflats)

            return _d

        def process_defaults(_d):
            if defaults:
                _d = _d.update_with(defaults, overwrite=False)

            return _d

        def process_envelope(_d):
            if op.envelope:
                _d = slovar({op.envelope:_d})

            return _d

        _d = self._subset(op)
        _d = process_flats(_d)
        _d = process_show_as(_d)
        _d = process_assignments(_d)
        _d = process_trans(_d)
        _d = process_unflats(_d)
        _d = process_defaults(_d)
        _d = process_envelope(_d)

        return _d

    def get_by_prefix(self, prefix):
        if not isinstance(prefix, list):
            prefixes = [prefix]
        else:
            prefixes = prefix

        _d = slovar()
        for kk, vv in list(self.items()):
            for pref in prefixes:
                _pref = pref[:-1]

                if pref.endswith('*'):
                    if kk.startswith(_pref):
                        ix = _pref.rfind('.')
                        if ix > 0:
                            _pref = _pref[:ix]
                            kk = kk[len(_pref)+1:]
                        _d[kk] = vv
                else:
                    if kk == pref:
                        ix = _pref.rfind('.')
                        if ix > 0:
                            _pref = _pref[:ix]
                            kk = kk[len(_pref)+1:]

                        _d[kk]=vv

        return _d

    def _subset(self, op):
        _d = slovar()

        if op.star:
            _d = self.copy()

        exp_only = op.exp_only[:]
        only_nested_flds = []

        if exp_only:
            for fld in exp_only:
                if fld in self:
                    _d[fld] = self[fld]
                else:
                    try:
                        if fld.endswith('.*'):
                            val = self.nested_get(fld)
                            if isinstance(val, dict):
                                # checking if val keys will overwrite the self
                                # conflict = self.set_keys() & val.set_keys()
                                # if conflict and op.star:
                                #     raise self.missing_key_error_klass(
                                #         'conflict with `%s` field. Reducing to a existing name' % conflict)
                                op.exp_only.extend(val.keys())
                                _d.update(val)
                            else:
                                raise self.bad_value_error_klass('%s must be dict, got %s' % (val, type(val)))
                        elif fld.endswith('*'):
                            _d.update(self.get_by_prefix(fld))
                        else:
                            _d[fld] = self.nested_get(fld)

                        only_nested_flds.append(fld)
                    except (KeyError, IndexError):
                        pass

        if op.exclude:
            _d = _d or self
            _d = _d.remove(op.exclude)

        if only_nested_flds and isinstance(_d, dict):
            _d = _d.unflat(only_nested_flds)

        return _d

    def subset(self, keys, defaults={}):
        if not keys:
            return slovar()

        return self._subset(process_fields(keys)).merge_with(defaults)

    def remove(self, keys, flat=False):

        def _remove_branch(path, _d):
            for key in list(_d.keys()):
                if key.startswith(path):
                    _d = _d.pop(key)

        if isinstance(keys, str):
            keys = [keys]

        _self = self.flat() if flat else self.copy()

        for k in keys:
            if '*' in k:
                _remove_branch(k.replace('*', ''), _self)
            else:
                _self.pop(k, None)

        return _self.unflat() if flat else _self

    def update(self, d_):
        super(slovar, self).update(slovar(d_))
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

    def nested_get(self, fld):
        _d = self.copy()

        if fld in _d or '.' not in fld:
            return _d[fld]

        for kk in fld.split('.'):
            if '*' == kk:
                break
            # if its a list then access it by index
            if isinstance(_d, list):
                if kk.isdigit():
                    kk = int(kk)
                else:
                    val_lst = []
                    for it in _d:
                        if isinstance(it, slovar):
                           val_lst.append(it.nested_get(kk))
                    return val_lst

            _d = _d[kk]

        return _d

    def nested_in(self, fld):
        if fld in self:
            return True
        elif '.' not in fld:
            return False

        inner = self
        for kk in fld.split('.'):
            if isinstance(inner, dict) and kk in inner:
                inner = inner[kk]
            else:
                return False

        return True

    def nested_pop(self, flds):
        self_d = self.copy()

        if isinstance(flds, str):
            flds = [flds]

        def _pop(fld):
            if fld in self or '.' not in fld:
                self_d.pop(fld)
                return self_d

            parts = fld.split('.')
            _d = self_d

            for kk in parts[:-1]:
                if isinstance(_d, list):
                    kk = int(kk)
                _d = _d[kk]

            try:
                kk = parts[-1]
                if isinstance(_d, list):
                    kk = int(kk)
                _d.pop(kk)

            except (KeyError, IndexError) as e:
                pass

        for fld in flds:
            _pop(fld)

        return self_d

    def get_tree(self, prefix, defaults={}, sep='.'):
        if prefix[-1] != '.':
            prefix += sep

        _dict = slovar(defaults)
        for key, val in list(self.items()):
            if key.startswith(prefix):
                _k = key.partition(prefix)[-1]
                _dict[_k] = val
        return _dict

    def mget(self, keys):
        _d = slovar()
        for it in self:
            if it in keys:
                _d[it] = self[it]
        return _d

    def mpop(self, keys):
        for it in keys:
            self.pop(it, None)

    def has(self, keys, check_type=str,
            err='', _all=True, allow_missing=False,
            allowed_values=[], forbidden_values=[]):
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

                if self_flat[key] in forbidden_values:
                    error_msg('`%s`=`%s` value is not allowed' % (key, self_flat[key]))

            elif not allow_missing:
                if allowed_values:
                    error_msg(missing_key_error(check_type, key))
                else:
                    error_msg('Missing key: `%s`' % key)

        if (errors and _all) or (not _all and len(errors) >= len(keys)):
            raise self.bad_value_error_klass('.'.join(errors))

        return True

    def transform(self, rules):
        _d = slovar()
        flat_dict = self.flat()

        for path, val in list(flat_dict.items()):
            if path in rules:
                _d.merge(slovar.from_dotted(rules[path], val))

        return _d

    def flat_keys(self, keys, keep_lists=True, sep='.'):
        self_ = self.copy()
        for key in keys:
            val = self_.subset(key)
            if val and isinstance(val, dict):
                self_ = self_.nested_pop(key)
                self_.update(val.flat(keep_lists=keep_lists, sep=sep))

        return self_

    def flat(self, keys=[], keep_lists=True, sep='.'):
        if keys:
            return self.flat_keys(keys, keep_lists=keep_lists, sep=sep)

        return slovar(flat(self, keep_lists=keep_lists, sep=sep))

    def unflat(self, only=[]):
        return slovar(unflat(self, only))

    def set_default(self, name, val):
        cls = slovar
        if name not in self.flat():
            self.merge(cls.from_dotted(name, val))
        return val

    def with_defaults(self, **defaults):
        return self.update_with(defaults, overwrite=False)

    def fget(self, key, *arg, **kw):
        return self.flat().get(key, *arg, **kw)

    def update_with(self, _dict, overwrite=True, append_to=None,
                                                 append_to_set=None,
                                                 flatten=None,
                                                 merge_to=None,
                                                 remove_from=None):

        self_dict = self.copy()
        if not _dict:
            return self_dict

        def process_append_to_param(_lst):
            if isinstance(_lst, str):
                _lst = [_lst]

            if not _lst:
                return {}

            _d = {}
            for each in (_lst or []):
                k,_,sk = each.partition(':')
                _d[k]=sk

                #reference to nested field?
                if '.' in k and (not flatten or (isinstance(flatten, list) and k.split('.')[0] not in flatten)):
                    raise self.bad_value_error_klass(
                        'list operation referrers to nested field `%s` without flattening.'
                        ' forgot to pass `flatten=%s`?' % (k, k.split('.')[0]))
            return _d

        append_to = process_append_to_param(append_to)
        append_to_set = process_append_to_param(append_to_set)
        merge_to = process_append_to_param(merge_to)
        remove_from = process_append_to_param(remove_from)

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
                    if not each:
                        log.debug('Empty item in the `%s:%s` list.Skip.', key, set_key)
                        continue

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

        def _merge_to(self_dict, key, val):
            set_key = merge_to.get(key)
            new_lst = []
            new_keys = []

            if not set_key:
                raise self.bad_value_error_klass('merge_to must contain a set key')

            if not isinstance(val, list):
                val = [val]

            for each in self_dict.get(key, []):
                if each.get(set_key):
                    for it in val:
                        if not it.get(set_key):
                            continue

                        if it[set_key] == each[set_key]:
                            each = each.update_with(it)

                        new_keys.append(it[set_key])

                new_lst.append(each)

            return new_lst

        def _remove_from(self_dict, key, val):
            set_key = remove_from.get(key)
            new_lst = self_dict.get(key, [])[:] # copy

            for vv in val:
                for vvv in new_lst:
                    if set_key:
                        if not isinstance(vv, dict) or not isinstance(vvv, dict):
                            raise self.bad_value_error_klass(
                                'set key `%s` can be specified only for dicts. Got : `%s` and `%s`' % (
                                                                                        set_key, vv, vvv))

                        if set_key in vv and vv[set_key] == vvv.get(set_key, None):
                            new_lst.remove(vvv)
                    else:
                        if vv == vvv:
                            new_lst.remove(vvv)

            return new_lst

        def can_overwrite(key, overwrite, flat_overwrites):
            if overwrite == True:
                return True

            if isinstance(overwrite, list):
                if flatten == True:
                    return True

                for it in flat_overwrites:
                    if key.startswith('%s.'%it):
                        return True

                if key in overwrite:
                    return True

            return False

        flat_overwrites = set()
        if flatten:
            flat_keys = flatten if isinstance(flatten, list) else None
            self_dict = self_dict.flat(keys=flat_keys)
            _dict = _dict.flat(keys=flat_keys)

            if flat_keys and isinstance(overwrite, list):
                s_overwrites = set(overwrite)
                flat_overwrites = (set(flat_keys) & s_overwrites)
                overwrite = list(s_overwrites - flat_overwrites)

        for key, val in list(_dict.items()):

            if key in append_to:
                self_dict[key] = _append_to(self_dict, key, val)
            elif key in append_to_set:
                self_dict[key] = _append_to_set(self_dict, key, val)
            elif key in merge_to:
                self_dict[key] = _merge_to(self_dict, key, val)
            elif key in remove_from:
                self_dict[key] = _remove_from(self_dict, key, val)
            elif key not in self_dict:
                self_dict[key] = val
            elif overwrite and can_overwrite(key, overwrite, flat_overwrites):
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
        if not keys:
            return self.copy()

        poped = slovar()
        pop_keys = self.extract(keys).keys()
        for key in pop_keys:
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

    def key_diff(self, keys):
        return list(set(self.keys()) - set(keys))

    def key_union(self, keys):
        return list(set(self.keys()) | set(keys))

    def key_intersection(self, keys):
        return list(set(self.keys()) & set(keys))

    def diff(self, sl2, diff_fields=[], flat_keys=[]):

        _self = self

        if flat_keys:
            _self = _self.flat(keys=flat_keys)
            sl2 = sl2.flat(keys=flat_keys)

        self_diff = slovar()
        sl2_diff = slovar()
        _diff = slovar()

        if diff_fields:
            diff_fields = list(_self.extract(diff_fields).keys())

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

    def add_to_list(self, list_name, items, unique=False, position=None, sort_key=None):
        _self = self

        if list_name not in _self:
            _self[list_name] = []

        if not items:
            return _self

        if not isinstance(items, list):
            items = [items]

        if position is not None:
            for ix in range(len(items)):
                _self[list_name].insert(position+ix, items[ix])
        else:
            _self[list_name].extend(items)

        if unique:
            _self[list_name] = list(set(_self[list_name]))

        if sort_key:
            _self[list_name] = sorted(_self[list_name], key=sort_key)

        return _self

    def concat_values(self, sep=':'):
        concat = []

        _keys = sorted(self.keys())

        for kk in _keys:
            concat.append(str(self[kk]))

        return sep.join(_keys), sep.join(concat)

    def ordered_values(self, keys):
        return [self.get(kk) for kk in keys if kk in self]

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

    def set_keys(self):
        #useful for testing mainly
        return set(self.keys())
