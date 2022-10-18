''' Class that implements mutability of an object
If an attempt is made to modify an attribute of Immutable(object),
an ImmutableError exception is thrown.

NB. I tested that TChains etc. are not duplicated, i.e. that thing should not leak.
'''

class ImmutableError(Exception):
    '''Modifying an instance that was intendend to be mutable.
    '''
    pass

class Immutable(object):

    def __init__(self, wrapped):
        super(Immutable, self).__init__()
        object.__setattr__(self, '_wrapped', wrapped)

    def __getattribute__(self, item):
        return object.__getattribute__(self, '_wrapped').__getattribute__(item)

    def __setattr__(self, key, value):
        raise ImmutableError('Object {0} is immutable.'.format(self._wrapped))

    __delattr__ = __setattr__

    def __iter__(self):
        return object.__getattribute__(self, '_wrapped').__iter__()

    def __next__(self):
        return next(object.__getattribute__(self, '_wrapped'))

    def __getitem__(self, item):
        return object.__getattribute__(self, '_wrapped').__getitem__(item)
