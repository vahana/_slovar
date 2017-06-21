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
