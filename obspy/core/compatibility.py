# -*- coding: utf-8 -*-
"""
Py3k compatibility module
"""
import io
import sys

import numpy as np

PY2 = sys.version_info.major == 2


# optional dependencies
try:
    if PY2:
        import mock  # NOQA
    else:
        from unittest import mock  # NOQA
except:
    pass

if PY2:
    from string import maketrans
else:
    maketrans = bytes.maketrans


if PY2:
    string_types = (bytes, str, unicode)  # NOQA
    unicode_type = unicode  # NOQA
else:
    string_types = (bytes, str)  # NOQA
    unicode_type = str  # NOQA


# NumPy does not offer the from_buffer method under Python 3 and instead
# relies on the built-in memoryview object.
if PY2:
    def from_buffer(data, dtype):
        # For compatibility with NumPy 1.4
        if isinstance(dtype, unicode):  # noqa
            dtype = str(dtype)
        if data:
            return np.frombuffer(data, dtype=dtype).copy()
        else:
            return np.array([], dtype=dtype)
else:
    def from_buffer(data, dtype):
        return np.array(memoryview(data)).view(dtype).copy()  # NOQA


def is_text_buffer(obj):
    """
    Helper function determining if the passed object is an object that can
    read and write text or not.

    :param obj: The object to be tested.
    :return: True/False
    """
    # Default open()'ed files and StringIO (in Python 2) don't inherit from any
    # of the io classes thus we only test the methods of the objects which
    # in Python 2 should be safe enough.
    if PY2 and not isinstance(obj, io.BufferedIOBase) and \
            not isinstance(obj, io.TextIOBase):
        if hasattr(obj, "read") and hasattr(obj, "write") \
                and hasattr(obj, "seek") and hasattr(obj, "tell"):
            return True
        return False

    return isinstance(obj, io.TextIOBase)


def is_bytes_buffer(obj):
    """
    Helper function determining if the passed object is an object that can
    read and write bytes or not.

    :param obj: The object to be tested.
    :return: True/False
    """
    # Default open()'ed files and StringIO (in Python 2) don't inherit from any
    # of the io classes thus we only test the methods of the objects which
    # in Python 2 should be safe enough.
    if PY2 and not isinstance(obj, io.BufferedIOBase) and \
            not isinstance(obj, io.TextIOBase):
        if hasattr(obj, "read") and hasattr(obj, "write") \
                and hasattr(obj, "seek") and hasattr(obj, "tell"):
            return True
        return False

    return isinstance(obj, io.BufferedIOBase)


def round_away(number):
    """
    Simple function that rounds a number to the nearest integer. If the number
    is halfway between two integers, it will round away from zero. Of course
    only works up machine precision. This should hopefully behave like the
    round() function in Python 2.

    This is potentially desired behavior in the trim functions but some more
    thought should be poured into it.

    The np.round() function rounds towards the even nearest even number in case
    of half-way splits.

    >>> round_away(2.5)
    3
    >>> round_away(-2.5)
    -3

    >>> round_away(10.5)
    11
    >>> round_away(-10.5)
    -11

    >>> round_away(11.0)
    11
    >>> round_away(-11.0)
    -11
    """

    floor = np.floor(number)
    ceil = np.ceil(number)
    if (floor != ceil) and (abs(number - floor) == abs(ceil - number)):
        return int(int(number) + int(np.sign(number)))
    else:
        return int(np.round(number))


def python_2_unicode_compatible(cls):
    """
    A class decorator that defines __unicode__ and __str__ methods under Python
    2. Under Python 3, this decorator is a no-op.

    Take from the future package, original implementation comes from
    django.utils.encoding.
    """
    if PY2:
        cls.__unicode__ = cls.__str__
        cls.__str__ = lambda self: self.__unicode__().encode('utf-8')
    return cls
