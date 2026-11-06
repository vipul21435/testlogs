"""Map ids from different runners of the same Python suite to one key.

pytest names a test by path (``tests/test_a.py::Class::test_x[p]``), JUnit XML
written by pytest by dotted class and name (``tests.test_a.Class::test_x[p]``),
and ``unittest -v`` by dotted path (``tests.test_a.Class.test_x``). Normalising
all three to ``tests.test_a.Class.test_x[p]`` lets ``diff`` compare a pytest log
with a unittest log of the same suite. Parameter brackets are left untouched.
"""

from __future__ import annotations


def normalise_id(test_id: str) -> str:
    """Return a runner-neutral key for ``test_id``.

    The part before the first ``[`` is rewritten: a leading ``./`` is dropped, a
    ``.py`` path segment becomes a dotted module, and ``::`` becomes ``.``.
    Anything else (JS, go and cargo ids) passes through with ``::`` -> ``.``.
    """
    head, bracket, params = test_id.partition("[")
    parts = head.split("::")
    first = parts[0]
    while first.startswith("./"):
        first = first[2:]
    if first.endswith(".py"):
        first = first[:-3].replace("\\", "/").strip("/").replace("/", ".")
    return ".".join([first, *parts[1:]]) + bracket + params
