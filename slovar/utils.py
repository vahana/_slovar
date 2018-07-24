import logging

log = logging.getLogger(__name__)


def resolve(name, module=None):
    """Resole dotted name to python module
    """
    name = name.split('.')
    if not name[0]:
        if module is None:
            raise ValueError('relative name without base module')
        module = module.split('.')
        name.pop(0)
        while not name[0]:
            module.pop()
            name.pop(0)
        name = module + name

    used = name.pop(0)
    found = __import__(used)
    for n in name:
        used += '.' + n
        try:
            found = getattr(found, n)
        except AttributeError:
            __import__(used)
            found = getattr(found, n)

    return found


def maybe_dotted(module, throw=True):

    def _import(module):
        if isinstance(module, str):
            module, _, cls = module.partition(':')
            module = resolve(module)
            if cls:
                return getattr(module, cls)

        return module

    if throw:
        return _import(module)
    else:
        try:
            return _import(module)
        except ImportError as e:
            log.error('%s not found. %s' % (module, e))


def fuzzy_match(name1, name2):
    import jellyfish

    """
        match_rating_comparision - phonetic comparison. works on 5 chars and more. returns None if < 4 chars
        jaro_distance - string-edit distance.
            values are floats between [0-1], where 0 is completely dissimilar strings and 1 is identical
    """

    n1 = str(name1.upper())
    n2 = str(name2.upper())

    return dict(
            mra = jellyfish.match_rating_comparison(n1, n2),
            jaro_distance = round(jellyfish.jaro_distance(n1, n2), 1)
        )

def fuzzy_sort(n1, nn, cuttoff=0.8):
    """
        will sort nn by the best fuzzy match with n1 using fuzzy_match method in this module.
    """

    matches = []

    for each in nn:
        match = fuzzy_match(n1, each)
        if match['mra'] and match['jaro_distance'] >= cuttoff:
            matches.append([each, match])

    def _key_func(xx):
        return xx[1]['jaro_distance']

    if matches:
        return sorted(matches, key=_key_func, reverse=True)


