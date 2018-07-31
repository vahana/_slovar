import time
import json
import pytest
from slovar import slovar


LOREM = 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nunc ut dictum nibh, non congue dolor. Nulla sollicitudin nunc ac nisl vestibulum auctor. Sed molestie dignissim feugiat. Etiam placerat justo arcu, et euismod sapien varius eu. Maecenas pellentesque, sapien non sagittis dapibus, tellus odio porttitor est, sit amet congue lorem nisl in nulla. Nullam rhoncus nisl tellus, eu sodales ligula eleifend quis. Cras accumsan in purus sit amet efficitur. Mauris et felis varius, mollis massa vel, vestibulum turpis. Vivamus euismod libero a lacus ultricies, quis convallis mauris tempus. Vivamus commodo gravida hendrerit.'


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
            'iii': [
                {'j': LOREM},
                {'jj': LOREM},
            ]
        },
        e={
            'i': LOREM,
            'ii': LOREM,
            'iii': LOREM,
            'iv': LOREM,
            'v': LOREM,
            'vi': LOREM,
            'vii': LOREM,
            'viii': LOREM,
            'ix': LOREM,
            'x': LOREM,
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
        d = slovar(self.sample_d)
        args = ['a', 'b', 'c', 'd.ii.*']
        assert d.extract(['a', 'b', 'c', 'd.ii.*']) == {
            'a': self.sample_d['a'],
            'b': self.sample_d['b'],
            'c': self.sample_d['c'],
            'aa': self.sample_d['d']['ii']['aa'],
            'ab': self.sample_d['d']['ii']['ab'],
        }

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

    # @pytest.mark.skip('this is a bug. fix and enable.')
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


