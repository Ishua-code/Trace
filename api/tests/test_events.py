from datetime import datetime, timezone
from app.services.events import GENESIS, _hash


def test_hash_is_deterministic_and_chained():
    t = datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc)
    h1 = _hash(GENESIS, "x", 1, {"a": 1, "b": 2}, t)
    assert h1 == _hash(GENESIS, "x", 1, {"b": 2, "a": 1}, t)  # key order is irrelevant
    assert h1 != _hash(h1, "x", 1, {"a": 1, "b": 2}, t)       # prev_hash changes the result


def test_naive_and_aware_same_instant_match():
    aware = datetime(2026, 11, 14, 9, 0, tzinfo=timezone.utc)
    assert _hash(GENESIS, "x", None, {}, aware) == _hash(GENESIS, "x", None, {}, aware.replace(tzinfo=None))