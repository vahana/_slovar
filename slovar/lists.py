from slovar.strings import split_strip


def expand_list(param):
    _new = []
    if isinstance(param, (list, set)):
        for each in param:
            if isinstance(each, str) and each.find(',') != -1:
                _new.extend(split_strip(each))
            elif isinstance(each, (list, set)):
                _new.extend(each)
            else:
                _new.append(each)
    elif isinstance(param, str) and param.find(',') != -1:

        _new = split_strip(param)

    return _new


def process_fields(fields, parse=True):
    # Avoid circular dependencies
    from slovar import slovar

    fields_only = []
    fields_exclude = []
    nested = {}
    show_as = {}
    show_as_r = {}
    transforms = {}
    assignments = {}
    flats = []
    envelope = None
    star = False
    negative = False

    if isinstance(fields, str):
        fields = split_strip(fields)

    for field in expand_list(fields):
        field = field.strip()

        if not field:
            continue

        if '*' == field:
            star = True
            continue

        if ':=' in field:
            kk, _, val = field.partition(':=')
            assignments[kk] = val
            continue

        field,_,trans = field.partition(':')
        trans = trans.split('|') if trans else []

        if 'flat' in trans:
            flats.append(field)
            trans.remove('flat')

        if field[0] == '-':
            field = field[1:]
            negative = True

        if parse and '__as__' in field:
            root,_,val = field.partition('__as__')
            if not root and val:
                envelope = val
                star = True
                continue
            else:
                show_as[root] = val or root.split('.')[-1]
                show_as_r[val or root.split('.')[-1]]=root
                field = root

        if trans:
            if field in show_as:
                transforms[show_as[field]] = trans
            else:
                transforms[field] = trans

        if parse and '.' in field:
            root = field.split('.')[0]
            nested[field] = root
            field = root

        if negative:
            fields_exclude.append(field)
        else:
            fields_only.append(field)

    if star:
        fields_only = []
        fields_exclude =[]

    return slovar({
             'fields': fields,
             'only': fields_only,
             'exclude':fields_exclude,
             'nested': nested,
             'show_as': show_as,
             'show_as_r': show_as_r,
             'transforms': transforms,
             'assignments': assignments,
             'star': star,
             'flats': flats,
             'envelope': envelope})


def union_fields(f1, f2):
    f1 = process_fields(f1)
    f2 = process_fields(f2)

    'a,b__as__bb,c.d,e.f__as__g,*'
    'a,x,c'


def sort_list(items, by='', reverse=False):
    'sort generic list of basic type or nested dicts'

    _items = []
    none_items = []

    if not by:
        return sorted(items, reverse=reverse)

    for each in items:
        if isinstance(each, dict):
            val = each.get(by)

            if val is None:
                none_items.append(each)
                continue

            _items.append(each)

    sorted_list = sorted(_items, key=lambda x: x.get(by), reverse=reverse)

    if reverse:
        return sorted_list + none_items
    else:
        return none_items + sorted_list






