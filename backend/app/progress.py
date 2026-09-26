"""Progress reporting for long pipeline steps: callers pass `progress(done, total)`, or nothing."""

from collections.abc import Callable

Progress = Callable[[int, int], None] | None


def report(progress: Progress, done: int, total: int) -> None:
    if progress is not None:
        progress(done, total)
