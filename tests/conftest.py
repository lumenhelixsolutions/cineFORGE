"""Root pytest configuration for CineForge."""


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    # Move e2e tests to the end of the queue.
    # pytest-playwright starts a running event loop in the main thread which
    # conflicts with pytest-asyncio's per-test loop creation. Running e2e
    # tests last avoids breaking async unit/integration tests.
    e2e_items = [item for item in items if "e2e" in item.nodeid]
    other_items = [item for item in items if "e2e" not in item.nodeid]
    items[:] = other_items + e2e_items
