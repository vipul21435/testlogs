"""A run stopped part way: the second test raises KeyboardInterrupt, as a timeout would."""


def test_first():
    pass


def test_interrupted():
    raise KeyboardInterrupt


def test_never_run_a():
    pass


def test_never_run_b():
    pass
