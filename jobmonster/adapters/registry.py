from __future__ import annotations

from jobmonster.adapters.assisted import assisted_adapters
from jobmonster.adapters.base import AdapterRegistry
from jobmonster.adapters.generic import GenericFormAdapter
from jobmonster.adapters.greenhouse import GreenhouseAdapter
from jobmonster.adapters.lever import LeverAdapter


def default_registry(allow_generic: bool = False) -> AdapterRegistry:
    adapters = [
        GreenhouseAdapter(),
        LeverAdapter(),
        *assisted_adapters(),
    ]
    if allow_generic:
        adapters.append(GenericFormAdapter())
    return AdapterRegistry(adapters)
