"""A module that fails to import: pytest stops before running any test."""

import module_that_does_not_exist  # noqa: F401


def test_unreachable():
    pass
