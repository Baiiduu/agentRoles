from __future__ import annotations

from .models import DEFAULT_REPO_URL, SoftwareSupplyChainUiSettings

__all__ = [
    "DEFAULT_REPO_URL",
    "SoftwareSupplyChainUiSettings",
    "SoftwareSupplyChainUiSettingsFacade",
]


def __getattr__(name: str):
    if name == "SoftwareSupplyChainUiSettingsFacade":
        from .facade import SoftwareSupplyChainUiSettingsFacade

        return SoftwareSupplyChainUiSettingsFacade
    raise AttributeError(name)
