# Slovar

Slovar is named dicts on steroids (cheesy!) with extra functionalities (lots of them). Widely used in [prf](https://github.com/vahana/prf), [jobs](https://github.com/vahana/jobs) and [datasets](https://github.com/vahana/datasets).

Some of more prominent features are:

1. flattening/unflattening

2. rich extracting

3. subsetting

4. typecasting/type converting

5. dot notation access

6. update/merge



## Setting up & testing

    mkvirtualenv slovar_test #or any other way of venv
    pip install -r requirements.test
    pytest
    pytest benchmarks/



## Examples:

```python
In [1]: from slovar import slovar

In [2]: d = slovar({'a':1, 'b': 2, 'c.c1': '11'})

In [3]: d
Out[3]: {'a': 1, 'b': 2, 'c.c1': '11'}

In [4]: d.unflat()
Out[4]: {'a': 1, 'b': 2, 'c': {'c1': '11'}}

In [5]: d.unflat().extract('c.c1')
Out[5]: {'c': {'c1': '11'}}

In [9]: d.unflat().extract('c').c.asint('c1')
Out[9]: 11


In [10]: d
Out[10]: {'a': 1, 'b': 2, 'c.c1': '11'}

In [11]: dd = d.unflat()

In [12]: dd.c.c1
Out[12]: '11'

In [14]: dd.flat() == d
Out[14]: True

```
