"""
Defines the generic `Flow` class.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, TypeVar, Generic

# We use '...' to indicate that steps may be skipped. This workaround allows us
# to refer to the ellipsis' type. See github.com/python/typing/issues/684
if TYPE_CHECKING:
    from builtins import ellipsis
else:
    ellipsis = type(Ellipsis)

T = TypeVar('T')


class Flow(Generic[T]):
    """
    A flow is used to capture a sequence of steps, possibly skipping over any
    number of them. The sequence may branch into disjunctions or conjunctions
    and it is 'reversed' (that is, specified from end to beginning). This
    allows for a convenient tree-like notation, but it may trip you up.

    For succinct notation, lists are interpreted as sequential flows and the
    ellipsis indicates we may skip any number of steps.

    For example, the following flow of type `Flow[int]` describes a flow ending
    in 99, where 3 results from steps 1 and 2.

    [99, ..., 3, AND(1, 2)]
    """

    @staticmethod
    def shorthand(value: T | Flow[T] | list[T | Flow[T]]) -> T | Flow[T]:
        """
        Translate shorthand data structures (ellipsis for skips, lists for
        sequences) to real flows.
        """
        assert value != ..., "ellipses may only occur in sequences"
        return Sequence(*value) if isinstance(value, list) else value


class Sequence(Flow[T]):
    def __init__(self, *items: ellipsis | T | Flow[T]):
        assert items

        self.items: list[T | Flow[T]] = []
        self.skips: list[bool] = []

        skip: bool = False
        for current in items:
            if current == ...:
                skip = True
            else:
                assert not isinstance(current, ellipsis)
                self.items.append(Flow.shorthand(current))
                self.skips.append(skip)
                skip = False
        self.skips.append(skip)

        assert len(self.items) == len(self.skips) - 1

    def __iter__(self) -> Iterator[tuple[bool, T | Flow[T], bool]]:
        return iter(zip(self.skips, self.items, self.skips[1:]))


class FlowBranch(Flow[T]):
    def __init__(self, *items: T | Flow[T]):
        assert items
        self.items = [Flow.shorthand(x) for x in items]


class AND(FlowBranch[T]):
    """
    Indicate which paths must occur conjunctively. That is, every path must
    occur somewhere --- possibly on distinct, parallel branches, possibly on
    the same branch.
    """
    pass


class OR(FlowBranch[T]):
    """
    Indicate which paths can occur disjunctively. That is, at least one path
    must occur somewhere.
    """
    pass
