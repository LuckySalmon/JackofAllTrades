from collections.abc import Callable, Generator
from typing import Protocol, TypeVar, final
from typing_extensions import Self


@final
class Targetable(Protocol):
    def __mul__(self, other: float, /) -> Self:
        ...

    def __add__(self, other: Self, /) -> Self:
        ...

    def __sub__(self, other: Self, /) -> Self:
        ...


T = TypeVar('T', bound=Targetable)


def pid(
    p: float = 0, i: float = 0, d: float = 0, *, zero: Callable[[], T] = float
) -> Generator[T, tuple[T, float], None]:
    integral_term = zero()
    derivative_term = zero()
    error, dt = yield zero()
    while True:
        previous_error = error
        error, dt = yield (error * p) + integral_term + derivative_term
        integral_term += (error + previous_error) * (i * dt / 2)
        derivative_term = (error - previous_error) * (d / dt) if dt else zero()
