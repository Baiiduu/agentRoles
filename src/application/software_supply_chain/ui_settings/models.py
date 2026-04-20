from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_REPO_URL = "https://github.com/Baiiduu/agentRoles"


@dataclass
class SoftwareSupplyChainUiSettings:
    current_repo_url: str
    saved_repo_urls: list[str] = field(default_factory=list)
