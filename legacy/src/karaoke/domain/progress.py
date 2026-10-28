from typing import Protocol, runtime_checkable


@runtime_checkable
class ProgressReporter(Protocol):
    def report(self, step: str, percent: int) -> None: ...
    def check_cancelled(self) -> None: ...


class NoopProgressReporter:
    def report(self, step: str, percent: int) -> None:
        pass

    def check_cancelled(self) -> None:
        pass
