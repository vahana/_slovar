import json
from datetime import date, datetime


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat().split(".")[0]
        try:
            return super(JSONEncoder, self).default(obj)
        except TypeError:
            return str(obj)  # fallback to unicode


def json_dumps(body):
    return json.dumps(body, cls=JSONEncoder)
