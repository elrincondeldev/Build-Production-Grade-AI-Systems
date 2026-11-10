"""Small in-memory LRU of recent scores, so /v1/explain/{id} can explain them.

⚠️ Teaching point (lesson 1.2): in-memory state makes a service *stateful*.
With two replicas behind a load balancer, the explain request may hit the
replica that never scored that transaction and return 404. Production systems
put this in a shared store (Redis, a database) or make the call self-contained.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Generic, TypeVar

V = TypeVar("V")


class LRUStore(Generic[V]):
    def __init__(self, max_items: int = 1000) -> None:
        self.max_items = max_items
        self._items: OrderedDict[str, V] = OrderedDict()

    def put(self, key: str, value: V) -> None:
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self.max_items:
            self._items.popitem(last=False)

    def get(self, key: str) -> V | None:
        value = self._items.get(key)
        if value is not None:
            self._items.move_to_end(key)
        return value
