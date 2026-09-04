from abc import ABCMeta, abstractmethod


def todict(obj, classkey=None):
    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[k] = todict(v, classkey)
        return data
    elif hasattr(obj, "_ast"):
        return todict(obj._ast())
    elif hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict([(key, todict(value, classkey))
                     for key, value in obj.__dict__.items()
                     if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj


def _strip_none(value):
    """Recursively drop ``None`` values from dicts (and dicts nested in lists).

    Unlike a shallow comprehension this also removes ``None`` fields inside
    nested models (e.g. ``NodeBilling`` inside ``NodeCompleted``), so a partial
    update never carries a null that would clobber an untouched column.
    """
    if isinstance(value, dict):
        return {k: _strip_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_strip_none(v) for v in value]
    return value


class BaseModel(metaclass=ABCMeta):

    def object_decoder(self, data: dict):
        for attr in dir(self):
            if attr.startswith("__"):
                continue

            if attr in data:
                setattr(self, attr, data[attr])

    def dict(self, exclude_none: bool = False):
        data = todict(obj=self)
        if exclude_none:
            data = _strip_none(data)
        return data
