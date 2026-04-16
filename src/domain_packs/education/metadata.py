from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EducationDomainMetadata:
    domain_name: str
    pack_version: str
    summary: str
    owner: str
    capability_tags: list[str] = field(default_factory=list)
    maturity: str = "prototype"


EDUCATION_DOMAIN_METADATA = EducationDomainMetadata(
    domain_name="education",
    pack_version="0.1.0",
    summary=(
        "Education domain pack for learner profiling, planning, practice, "
        "review, and adaptive tutoring workflows."
    ),
    owner="agentsRoles",
    capability_tags=[
        "education",
        "learner-modeling",
        "curriculum-planning",
        "exercise-generation",
        "review-feedback",
    ],
    maturity="prototype",
)
