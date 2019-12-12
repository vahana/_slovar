import time
import json
import pytest
from slovar import slovar


LOREM = 'Lorem'


class TestSlovarComplex(object):
    sample_d = slovar(
        a=1,
        b=LOREM,
        c=list(range(20)),
        d={
            'i': [LOREM] * 10,
            'ii': {
                'aa': LOREM,
                'ab': [5, 6, [7, 8, 9]],
            },
            'iii': [1,2,3,4],
            'iiii': [
                {'j': LOREM},
                {'jj': LOREM},
            ]
        },
        f=[[1, 2, 3], 4, 5],
        g=[1, 2, 4, [4, 5], 6],
        h=[1, 2, 4, [[4, 5], 6]],
    )

    def test_flat(self):
        d = slovar(self.sample_d)
        assert slovar(d.flat()).unflat() == self.sample_d

    def test_flat_lists(self):
        d = slovar(self.sample_d)
        assert slovar(d.flat(keep_lists=False)).unflat() == self.sample_d

    def test_unflat(self):
        d = slovar(self.sample_d).flat()
        assert d.unflat() == self.sample_d

    def test_unflat_lists(self):
        d = slovar(self.sample_d).flat(keep_lists=False)
        assert d.unflat() == self.sample_d

    def test_extract(self):
        d = slovar(self.sample_d)
        args = ['a', 'b', 'c']
        assert d.extract(args) == {
            'a': self.sample_d['a'],
            'b': self.sample_d['b'],
            'c': self.sample_d['c'],
        }

    def test_extract_with_defaults(self):
        _d = slovar(a=1,b=2)
        #adds the default
        assert _d.extract('a,d', defaults={'d':3}) == {'a':1, 'd':3}
        #does not overwrite with default if exists
        assert _d.extract('a,b', defaults={'b':3}) == {'a':1, 'b':2}

    def test_extract_nested(self):
        dd = slovar(self.sample_d)

        #get nested dict
        _d = dd.extract(['a', 'b', 'c', 'd.ii'])
        assert set(_d.flat().keys()) == set(['a', 'b', 'c', 'd.ii.aa', 'd.ii.ab'])

        #get nested list
        _d = dd.extract(['a', 'b', 'c', 'd.ii.ab'])
        assert set(_d.flat().keys()) == set(['a', 'b', 'c', 'd.ii.ab'])

        #get nested list item
        _d = dd.extract(['d.ii.ab.2'])
        assert set(_d.flat().keys()) == set(['d.ii.ab'])

    def test_extract_exclude(self):
        d = slovar(self.sample_d)
        args = ['-a', '-b', '-c', '-e', '-g', '-h']
        assert d.extract(args) == {
            'd': self.sample_d['d'],
            'f': self.sample_d['f'],
        }

    def test_subset(self):
        d = slovar(self.sample_d)
        args = ['a', 'b', 'd']
        assert d.subset(args) == {
            'a': self.sample_d['a'],
            'b': self.sample_d['b'],
            'd': self.sample_d['d'],
        }

    def test_subset_exclude(self):
        d = slovar(self.sample_d)
        args = ['-a', '-b', '-c', '-e', '-g', '-h']
        assert d.subset(args) == {
            'd': self.sample_d['d'],
            'f': self.sample_d['f'],
        }

    def test_update_with(self):
        # Include d in both to have a collision
        d = slovar(self.sample_d).subset(['a', 'b', 'd', 'g', 'h'])
        e = slovar(self.sample_d).subset(['c', 'd', 'e', 'f'])
        assert d.update_with(e) == self.sample_d

    def test_update_with_append_to(self):
        # Include d in both to have a collision
        d = slovar(self.sample_d).subset(['a', 'b', 'd', 'g', 'h'])
        e = slovar(self.sample_d).subset(['c', 'd', 'e', 'f'])
        a = []
        assert d.update_with(e, append_to=a) == self.sample_d

        d1 = slovar(
            a = [],
            aa = [1],
            aaa = [{'b':1, 'c':2}]
        )
        d2 = slovar(
            a = 1,
            aa = 2,
            aaa= [{'b':3, 'c': 3}, {'b':2, 'c': 33}]
        )

        d3 = d1.update_with(d2, append_to='aaa')
        assert d3.aaa == [{'b':1, 'c':2}, {'b':3, 'c': 3}, {'b':2, 'c': 33}]

        d3 = d1.update_with(d2, append_to='aaa:b')
        assert d3.aaa == [{'b':1, 'c':2}, {'b':2, 'c': 33}, {'b':3, 'c': 3}]

        d3 = d1.update_with(d2, append_to='aaa:-b')
        assert d3.aaa == [{'b':3, 'c': 3}, {'b':2, 'c': 33}, {'b':1, 'c':2}]

    def test_update_with_append_to_set(self):
        d1 = slovar(
            a = [],
            aa = [1],
            aaa = [{'b':1, 'c':2}]
        )
        d2 = slovar(
            a = 1,
            aa = 2,
            aaa= [{'b':1, 'c': 3}, {'b':2, 'c': 33}]
        )

        for ix in range(2):
            d3 = d1.update_with(d2, append_to_set=[
                    'a',
                    'aa',
                    'aaa:b'
            ])

            assert len(d3.a) == 1
            assert len(d3.aa) == 2
            assert len(d3.aaa) == 2

        d3 = d1.update_with({'x':1}, append_to='x')
        assert 'x' in d3

    def test_update_with_append_to_set2(self):
        d1 = slovar(
            a = [],
            aa = [1],
            aaa = [{'b':1, 'c':2}]
        )

        d3 = d1.update_with({'aaa':{'b': 1, 'c':11, 'd':33}}, append_to_set=['aaa:b'])
        assert d3.aaa[0]['c'] == 11
        assert d3.aaa[0]['d'] == 33

    def test_update_with_append_to_set_order(self):
        d1 = slovar(
            a = [
                dict(b = 10),
                dict(b = 20),
                dict(b = 30),
            ]
        )

        d3 = d1.update_with(dict(a=[dict(b=5), dict(b=15)]), append_to_set='a:-b')
        # assert d3.a == [{'b': 30}, {'b': 20}, {'b': 15}, {'b': 10}, {'b': 5}]

        d3 = d1.update_with(dict(a=[dict(b=5), dict(b=15)]), append_to_set='a:b')
        # assert d3.a == [{'b': 30}, {'b': 20}, {'b': 15}, {'b': 10}, {'b': 5}]

    def test_update_with_overwrite(self):
        d1 = slovar(
            a = {'b': 1},
            c = 2,
            d = [2]
        )

        d2 = d1.update_with({'c':1, 'd':3})
        assert d2.c == 1
        assert d2.d == 3

        d2 = d1.update_with({'c':1, 'd':3}, overwrite=False)
        assert d2.c == 2
        assert d2.d == [2]

        d2 = d1.update_with({'d':1}, append_to='d')
        assert d2.d == [2,1]

        d2 = d1.update_with({'d':4}, append_to='d', overwrite=False)
        assert d2.d == [2,4]

    def test_update_with_flat(self):

        d1 = slovar(
            a = {'b':
                    {'c': 1},
                 'bb': 2},
        )

        d2 = slovar(
            a = {'b':
                    {'d': 2}}
        )

        d3 = d1.update_with(d2, flatten=True)
        assert d3.a.b.d == 2
        assert d3.a.b.c == 1

    def test_extract_with_assignment(self):
        assert slovar(a=1).extract('a:=2') == slovar(a='2')

    def test_update_with_flat_keys(self):
        d1 = slovar(
            a = slovar(b=1),
            c = slovar(d=2),
            e = 3
        )

        assert d1.flat() == slovar({'a.b':1, 'c.d':2, 'e':3})
        assert 'a' not in d1.flat()
        assert d1.flat(['a']) == slovar({'a.b':1, 'c':slovar(d=2), 'e':3})
        assert d1.flat(['a', 'e']) == slovar({'a.b':1, 'c':slovar(d=2), 'e':3})
        assert d1.flat(['e']) == d1

        d2 = d1.update_with(slovar(a=slovar(bb=4)))
        assert 'b' not in d2.a
        assert d2.a.bb == 4
        assert d2.c.d == 2

        d2 = d1.update_with(slovar(a=slovar(bb=4), c=slovar(ff=5)), flatten=True)
        assert 'b' in d2.a
        assert d2.a.bb == 4
        assert 'd' in d2.c
        assert d2.c.ff == 5

        #flatten only `a` and `c` should be overwritten
        d2 = d1.update_with(slovar(a=slovar(bb=4), c=slovar(ff=5)), flatten=['a'])
        assert 'b' in d2.a
        assert d2.a.bb == 4
        assert 'd' not in d2.c
        assert d2.c.ff == 5

    def test_extract_envelope(self):
        d1 = slovar(
            a = 1,
            b = slovar(c = 2)
        )

        # d2 = d1.extract('__as__d')
        # assert 'd' in d2
        # assert d2.d == d1
        # assert 'a' not in d2
        # assert 'b' not in d2
        # assert 'd.a' in d2.flat()
        # assert 'd.b.c' in d2.flat()

        d2 = d1.extract('a,__as__d')
        assert d2.d.set_keys() == set(['a'])

    def test_extract_assign(self):
        d1 = slovar(
            c = '123',
            b='345'
        )

        d2 = d1.extract('c__as__a.c:float,b__as__a.b:float,a.dd:=dd').unflat()
        assert d2.a.c == 123
        assert d2.a.b == 345
        assert d2.a.dd == 'dd'

    def test_update_with_merge_to(self):
        d1 = slovar(
            a = [
                dict(b=1, c=2),
                dict(b=11, c=22),
                dict(b=11, c=33),
                dict(c=44),
            ]
        )

        d1.update_with(slovar(a=1), merge_to='x')
        d1.update_with(slovar(), merge_to='a:b')

        with pytest.raises(Exception):
            d1.update_with(slovar(a=1), merge_to='a')

        #should not change d1 since there is not b=55 in it
        d2 = slovar(a={'b':55, 'c': 222})
        d3 = d1.update_with(d2, merge_to='a:b')
        assert d3 == d1

        d2 = slovar(a=[{'b':11, 'c': 222, 'd': 444}])
        d3 = d1.update_with(d2, merge_to='a:b')

        assert len(d3) == len(d1)
        assert 'd' not in d1.a

        assert d3.a[1]['c'] == 222
        assert d3.a[1]['d'] == 444

        assert d3.a[2]['c'] == 222
        assert d3.a[2]['d'] == 444

        d3 = d2.update_with(d1, merge_to='a:b')
        assert d3.a[0]['c'] == 33

    def test_unflat_extract(self):
        d1 = slovar({
                'a.b':1,
                'a.c': 2,
                'a.d':[1,2],
                'e': 1})

        d2 = d1.unflat().extract('a.b')
        assert 'a' in d2
        assert 'a.b' not in d2

        d2 = d1.extract(['a.b'])
        assert 'a.b' in d2
        assert d2['a.b'] == 1
        assert 'a.c' not in d2

        d2 = d1.unflat().extract('a')
        assert d2.set_keys() == set(['a'])

        d2 = d1.extract('a.d')
        assert d2.set_keys() == set(['a.d'])

        d2 = d1.unflat().extract('a.d')
        assert d2.flat().set_keys() == set(['a.d'])

    def test_subset2(self):
        d1 = slovar({
                'a.b':1,
                'a.c': 2,
                'a.d.d':[1,2],
                'e': 1,
            }).unflat()

        d2 = d1.subset('a.d.d,a.*')
        assert d2.set_keys() == set(['a', 'b', 'c', 'd'])
        assert d2.a.d.d == d2.d.d

    def test_reduce_extract(self):
        d1 = slovar({
                'a.b':1,
                'a.c': 2,
                'a.d.d':[1,2],
                'e': 1}).unflat()

        d2 = d1.extract('a.*')
        assert d2.set_keys() == set(['b', 'c', 'd'])

        d2 = d1.flat().extract('a.*')
        assert d2.set_keys() == set()

        d2 = d1.extract('a.d.d__as__dd,a.d.*')
        assert d2.flat().set_keys() == set(['dd', 'd'])

    def test_show_as(self):
        d1 = slovar({
                'a.b':1,
                'a.c': 2,
                'a.d.dd':[1,2],
                'a.d.bb': 'bb'}).unflat()

        d2 = d1.extract('a.d.dd__as__dlist')
        assert d2.set_keys() == set(['dlist'])

        d2 = d1.flat().extract('a.d.dd__as__dlist')
        assert d2.set_keys() == set(['dlist'])

        d2 = d1.extract('a.d.dd__as__dlist, a.d.dd')
        assert d2.set_keys() == set(['dlist', 'a'])

    def test_star(self):
        d1 = slovar({
                'a.b':1,
                'a.c': 2,
                'a.d.dd':[1,2],
                'e': 1}).unflat()

        d2 = d1.extract('a.d.dd__as__aa,*')
        assert d2.set_keys() == set(['aa', 'a', 'e'])

    def test_flat(self):
        d1 = slovar({
                'a.b':1,
                'a.c': 2,
                'a.d.dd':[1,2],
                'e': 1}).unflat()

        d2 = d1.flat(['a'])
        assert d2.set_keys() == set(['a.b', 'a.c', 'a.d.dd', 'e'])

    def test_nested_get(self):
        d1 = slovar({
            'e':[{'ee': 1, 'xx': 1}, {'ee': 2, 'yy': 1}]
        }).unflat()

        d2 = d1.nested_get('e.ee')
        assert set(d2) == set([1,2])

    def test_nested_pop(self):
        d1 = slovar({
                'a.b':1,
                'a.c': 2,
                'a.d.dd':[1,2],
                'e': 1}).unflat()

        d2 = d1.nested_pop('a.d.dd.0')
        assert d2.a.d.dd[0] == 2
        assert len(d2.a.d.dd) == 1

        assert 'a.d.dd' in d1.flat()
        d2 = d1.nested_pop('a.d.dd')
        assert 'a.d.dd' not in d2.flat()

        d2 = d1.nested_pop('a.d')
        d2 = d1.nested_pop('a')

        d2 = d1.nested_pop(['a.b', 'e'])
        assert d2.flat().set_keys() == set(['a.c', 'a.d.dd'])

    def test_mix1(self):
        d1 = slovar({
            'a': 1,
            'b': [1,2,3],
            'c.c': '1',
            'c.cc': [11,22,32],
            'd.d.d': 1,
            'd.d.dd': [111,222,333],
            'e':[{'ee': 1}, {'ee': 2}]
        }).unflat()

        fields = ['a', 'b', 'c.c__as__cc:int',
                                  'd.d', 'd.d.dd__as__ddd',
                                  'e.1',
                                  'g.g:=ggg',
                                  'd:unflat'
                                  ]

        d2 = d1.extract(fields, defaults={'f': 1})
        assert d2.set_keys() == set(['a', 'b', 'cc', 'd', 'ddd', 'e', 'f', 'g.g'])

    def test_reducer_with_show_as(self):
        d1 = slovar({
            'a': 1,
            'b': [1,2,3],
            'c.c': '1',
            'c.cc': [11,22,32],
            'd.d.d': 1,
            'd.d.dd': [111,222,333],
            'e':[{'a': {'b': 1, 'c': 2}, 'aa': 11}, {'a': {'b': 2}, 'aa': 22}]
        }).unflat()

        d2 = d1.extract('e.0.*,e.aa__as__aaa')
        assert d2.set_keys() == set(['a', 'aa', 'aaa'])
        assert d2['a'] == {'b': 1, 'c': 2}
        assert d2['aaa'] == [11,22]

    def test_flat_reducer(self):
        # if fields are flat originally, extract will treat them just as normal keys, not nested.
        # so doing nesting ops should not work

        d1 = slovar({
            'c.c': '1',
            'c.cc': [11,22,32],
            'd.d.d': 1,
        })

        d2 = d1.extract('c.*')
        assert not d2

        d2 = d1.extract('c*')
        assert d2.set_keys() == set(['c.c', 'c.cc'])

        d2 = d1.extract('d.d')
        assert not d2

    def test_unflat_show_as(self):
        d1 = slovar({
            'a': '1',
            'b': [11,22,32],
            'd.d': 1,
        })

        d2 = d1.extract(['a__as__aa.a', 'b__as__aa.b', 'aa:unflat', 'd.d'])
        assert d2.set_keys() == set(['aa', 'd'])

    def test_show_as_double(self):
        d1 = slovar({
            'a': '1',
            'b': [11,22,32],
            'd.d': 1,
        })

        d2 = d1.extract(['a__as__b', 'a__as__bb'])
        assert d2.set_keys() == set(['b', 'bb'])


    @pytest.mark.skip('nested trans is not implemented')
    def test_nested_trans(self):
        d1 = slovar({'abc': 1, 'geo': {'lat': '50.420907', 'lon': '9.414015'}})
        d2 = d1.extract('geo.lat:float,geo.lon:float,*')

        assert type(d2.geo.lat) == float
        assert 'abc' in d2

    def test_flat_unflat(self):
        d1 = slovar({
            'a': '1',
            'b': [{'bb': 11},22,32],
            'd.d': 1,
        }).unflat()

        d2 = d1.extract('b.0.bb:=111,b:flatall|unflat')
        assert d2.set_keys() == set(['b'])
        assert d2.b[0]['bb'] == '111'

    def test_as_star(self):
        d1 = slovar({
            'a': '1',
            'b': [{'bb': 11,},22,32],
            'd.d': 1,
        }).unflat()

        d2 = d1.extract('d.d__as__d.ddd,*')
        assert d2.flat().set_keys() == set(['d.ddd', 'a', 'b', 'd'])

    def test_multi_nested_with_show_as(self):
        d1 = slovar({
            'x': 0,
            'a.a': '1',
            'a.b': [{'bb': 11},22,32],
            'a.c': 1,
            'a.d': 'd',
        }).unflat()

        d2 = d1.extract('a.a,a.b,a.c,x__as__xx')
        assert d2.set_keys() == set(['a', 'xx'])
        assert d2.flat().set_keys() == set(['a.a', 'a.b', 'a.c', 'xx'])

    def test_default_assign(self):
        d1 = slovar(a=1,b=2,c=3)

        d2 = d1.extract('a:=10:int')
        assert d2.a == 10

        d2 = d1.extract('a:=10:int|default,b')
        assert d2.a == 1
        assert d2.set_keys() == set(['a', 'b'])

        d2 = d1.extract('d:=100:int|default')
        assert d2.d == 100

        d2 = d1.extract('a:=10:int|default,*')
        assert d2.set_keys() == set(['a', 'b', 'c'])

    def test_update_with_remove_from(self):
        d1 = slovar({
            'a': [],
            'aa.a': [1,2,3],
            'aa.b': [{'a':1}, {'b':2}],
            'aa.c': [{'a': 1}, 2, 3],
        }).unflat()

        d2 = slovar({
            'a': [1],
            'aa.a': [2],
            'aa.b': [{'a':1}, {'x': 1}],
            'aa.c': [3]
        }).unflat()

        d3 = d1.update_with(d2, remove_from='a')
        assert d3.a == d1.a

        d3 = d1.update_with(d2, remove_from='aa.a', flatten=['aa'])
        assert d3.aa.a == [1,3]

        with pytest.raises(ValueError):
            d3 = d1.update_with(d2, remove_from='aa.a:xxx', flatten=['aa'])

        d3 = d1.update_with(d2, remove_from='aa.c', flatten=['aa'])
        assert d3.aa.c == [{'a':1}, 2]

        with pytest.raises(ValueError):
            d3 = d1.update_with(d2, remove_from='aa.c:xxx', flatten=['aa'])

        d3 = d1.update_with(d2, remove_from='aa.b:a', flatten=['aa'])
        assert 'a' not in d3.aa.b

    def test_update_with_nested_list(self):

        d1 = slovar({
            'a': [],
            'aa.a': [1,2,3],
            'aa.b': [{'a':1}, {'b':2}],
            'aa.c': [{'a': 1}, 2, 3],
        }).unflat()

        d2 = slovar({
            'a': [1],
            'aa.a': [4],
            'aa.b': [{'a':1}, {'x': 1}],
            'aa.c': [3]
        }).unflat()

        d3 = d1.update_with(d2, append_to_set='aa.a', flatten='aa.a')
        assert d3.aa.a == [1,2,3,4]

    def test_nested_in(self):
        d1 = slovar({
            'a.b.c': 1,
            'x': 2
            }).unflat()

        assert d1.nested_in('a')
        assert d1.nested_in('a.b')
        assert d1.nested_in('a.b.c')
        assert d1.nested_in('x')
        assert not d1.nested_in('a.y')
        assert not d1.nested_in('x.y')

    def test_simple_combo1(self):
        d1 = slovar({
            'a.b.b1': 1,
            'a.b.b2': 2,
            'd.dd': {}
            }).unflat()

        d2 = d1.extract('d, a.b.b1__as__bb1')
        assert 'd' in d2
        assert 'bb1' in d2


    def test_flat_empty(self):
        d1 = slovar({
            'a.b.b1': 1,
            'a.b.b2': 2,
            'd.dd': {}
            }).unflat()

        d2 = d1.flat()
        assert 'd.dd' in d2

