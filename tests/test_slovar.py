from datetime import datetime
import pytest
from slovar import slovar
from slovar.operations.dictionaries import merge
from slovar.operations.lists import expand_list
from slovar.errors import DValueError


class TestSlovar():
    def test(self):
        dset = slovar(a=1)

        assert isinstance(dset, dict) is True
        assert dset.a == dset['a']

        dset.a = 10
        assert dset['a'] == 10

        dset.b = 2
        assert dset['b'] == dset.b

        dset.d = dict(a=1)
        assert dset.d.a == dset['d']['a']

        del dset.b
        assert 'b' not in dset

    def test_subset(self):
        dset = slovar(a=1, b=2, c=3)

        assert set(dset.subset(['a', 'c']).keys()) == set(['a', 'c'])
        assert set(dset.subset(['-a']).keys()) == set(['b', 'c'])

        # can not have both negative and positive.
        with pytest.raises(Exception):
            dset.subset(['-a', 'b'])

        assert dset.subset(['NOTTHERE']) == {}
        assert dset.subset(['-NOTTHERE']) == dset
        assert dset.subset([]) == {}

        assert set(dset.subset(['a', 'NOTTHERE']).keys()) == set(['a'])
        assert set(dset.subset(['-a', '-NOTTHERE']).keys()) == set(['b', 'c'])

    def test_remove(self):
        dset = slovar(a=1, b=2, c=3)

        assert dset.remove([]) == dset
        assert dset.remove(['NOTTHERE']) == dset
        assert dset.remove(['b', 'c']) == dict(a=1)

    def test_update(self):
        dset = slovar(a=1, b=2, c=3)
        assert dset.update(dict(d=4)).d == 4
        assert dset.d == 4

    def test_copy(self):
        dset = slovar(a=1, b=2, c=3)
        dset_copy = dset.copy()
        dset_alias = dset

        assert dset == dset_copy
        assert id(dset) == id(dset_alias)
        assert id(dset) != id(dset_copy)

    def test_pop_by_values(self):
        dset = slovar(a=1, b=2, c=2)
        dset_copy = dset.copy()
        dset.pop_by_values(666)
        assert dset == dset_copy

        dset.pop_by_values(2)
        assert dset.keys() == ['a']
        assert dset != dset_copy

    def test_merge(self):
        d1 = {}
        merge(d1, {})
        assert d1 == {}

        merge(d1, dict(a=1))
        assert d1 == dict(a=1)

        # XXX This doesn't raise anymore. It should.
        d1 = dict(a={})
        # with pytest.raises(ValueError):
        #     merge(d1, dict(a=1))

        merge(d1, dict(a={}))
        assert d1 == dict(a={})

        merge(d1, dict(a=dict(b=1)))
        assert d1 == dict(a=dict(b=1))

        d1 = dict(a=dict(c=1))
        merge(d1, dict(a=dict(b=1)))
        assert d1 == {'a': {'c': 1, 'b': 1}}

        d1 = slovar(a={})
        d1.merge({})

    def test__getattr__(self):
        d1 = slovar()
        with pytest.raises(AttributeError):
            d1.NOTTHERE
        d1['a'] = 1

    def test__contains__(self):
        d1 = slovar(a=dict(b=1))
        assert ['a', 'b'] in d1

    def test_to_slovar(self):
        d1 = slovar(a=[dict(c=1), 1])
        assert isinstance(d1.a[0], slovar)

    def test_get_tree(self):
        d1 = slovar({'a.b':1, 'a.c':2})
        assert d1.get_tree('a') == {'c': 2, 'b': 1}

    def test_from_dotted(self):
        assert slovar.from_dotted('a.b.c', 1) == {'a': {'b': {'c': 1}}}

    def test_has(self):
        d1 = slovar(a=1)
        with pytest.raises(DValueError):
            d1.has('a', check_type=basestring)

        assert d1.has('a', check_type=int) == True

        with pytest.raises(DValueError):
            d1.has('b', check_type=int)

    def test_expand_list(self):
        assert expand_list(None) == []

        assert expand_list('1,2,3') == ['1', '2', '3']
        assert expand_list([1,2,3]) == [1,2,3]
        assert expand_list([1,2,[3,4]]) == [1,2,3,4]

        assert expand_list([1,2,'3,4']) == [1,2,'3','4']
