import time


def now() -> int:
    """Epoch seconds, UTC. Patched in tests."""
    return int(time.time())
