import pytest

import svcs


def test_basic():
    """
    Does basic inheritance work?
    """
    with (
        svcs.Registry() as reg,
        svcs.Container(registry=reg) as c1,
        c1.fork() as c2,
    ):
        reg.register_value(dict, {"hi"})
        c1.get(dict)  # Instantiate
        assert c1.get(dict) is c2.get(dict)


def test_local_parent():
    """
    Check that a child container can access the parent's local registry
    """
    with (
        svcs.Registry() as reg,
        svcs.Container(registry=reg) as c1,
        c1.fork() as c2,
    ):
        c1.register_local_value(dict, {"hi"})
        c1.get(dict)  # Instantiate
        assert c1.get(dict) is c2.get(dict)


def test_local_child():
    """
    Check that a parent doesn't access a child's local registry
    """
    with (
        svcs.Registry() as reg,
        svcs.Container(registry=reg) as c1,
        c1.fork() as c2,
    ):
        c2.register_local_value(dict, {"hi"})
        c2.get(dict)  # Instantiate
        with pytest.raises(svcs.exceptions.ServiceNotFoundError):
            c1.get(dict)
        assert c2.get(dict)


def test_grandparent():
    """
    Check that inheritance works with grandparents (and hopefully any number of greats)
    """
    with (
        svcs.Registry() as reg,
        svcs.Container(registry=reg) as c1,
        c1.fork() as c2,
        c2.fork() as c3,
    ):
        reg.register_value(dict, {"hi"})
        c1.get(dict)  # Instantiate
        assert c3.get(dict) is c1.get(dict)


def test_jagged_lifetimes():
    """
    Check what happens when container lifetimes aren't properly nested.
    """
    with svcs.Registry() as reg, svcs.Container(registry=reg) as c1:
        reg.register_value(dict, {"hi"})
        cm = c1.fork()
        c2 = cm.__enter__()
        # Instantiate the item after c2's been created, so we can prove it's
        # not just a copy.
        val = c1.get(dict)
        assert val == {"hi"}

    # C1 is still live at this point, and C2 is pulling from it.

    assert c2.get(dict) == {"hi"}
    assert c2.get(dict) is val
    cm.__exit__(None, None, None)
