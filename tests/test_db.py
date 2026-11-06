from shop_assist import db


def test_get_checkpointer_uses_health_checked_connection_pool(monkeypatch):
    pool_args = {}
    pools = []
    checkpointers = []

    class FakePool:
        check_connection = object()

        def __init__(self, **kwargs):
            pool_args.update(kwargs)
            pools.append(self)

        def open(self, *, wait):
            self.wait = wait

    class FakeSaver:
        def __init__(self, pool):
            self.pool = pool
            self.setup_called = False
            checkpointers.append(self)

        def setup(self):
            self.setup_called = True

    monkeypatch.setattr(db, "ConnectionPool", FakePool)
    monkeypatch.setattr(db, "PostgresSaver", FakeSaver)
    db.get_checkpointer.clear()

    try:
        checkpointer = db.get_checkpointer()
    finally:
        db.get_checkpointer.clear()

    assert checkpointer is checkpointers[0]
    assert checkpointer.pool is pools[0]
    assert checkpointer.setup_called
    assert pools[0].wait is True
    assert pool_args["conninfo"] == db.DATABASE_URL
    assert pool_args["kwargs"]["autocommit"] is True
    assert pool_args["kwargs"]["prepare_threshold"] == 0
    assert pool_args["max_idle"] == 180
    assert pool_args["check"] is FakePool.check_connection
