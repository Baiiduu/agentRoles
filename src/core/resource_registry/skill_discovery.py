from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re


_FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


@dataclass(frozen=True)
class SkillSource:
    source_ref: str
    source_kind: str
    root_path: Path
    label: str
    notes: str = ""


@dataclass(frozen=True)
class DiscoveredSkill:
    skill_name: str
    name: str
    description: str
    source_kind: str
    source_path: str
    prompt_file: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class SkillDiscoveryConflict:
    conflict_kind: str
    skill_name: str
    sources: list[str]
    message: str


def default_skill_sources(project_root: Path) -> list[SkillSource]:
    sources: list[SkillSource] = []
    seen: set[Path] = set()

    def add(source_ref: str, source_kind: str, path: Path, label: str, notes: str = "") -> None:
        resolved = path.resolve()
        if resolved in seen or not resolved.exists():
            return
        seen.add(resolved)
        sources.append(
            SkillSource(
                source_ref=source_ref,
                source_kind=source_kind,
                root_path=resolved,
                label=label,
                notes=notes,
            )
        )

    add("project.default", "project", project_root / ".codex" / "skills", "Project .codex skills")

    codex_home = os.environ.get("CODEX_HOME", "").strip()
    if codex_home:
        add("codex_home.default", "codex_home", Path(codex_home) / "skills", "CODEX_HOME skills")

    return sources


def discover_skills(sources: list[SkillSource]) -> list[DiscoveredSkill]:
    return discover_skills_report(sources)["skills"]


def discover_skills_report(sources: list[SkillSource]) -> dict[str, list[object]]:
    discovered: dict[str, DiscoveredSkill] = {}
    collisions: dict[str, list[str]] = {}
    for source in sources:
        for prompt_file in sorted(source.root_path.rglob("SKILL.md")):
            skill_dir = prompt_file.parent
            relative_parent = skill_dir.relative_to(source.root_path).as_posix()
            skill_name = relative_parent.strip("./")
            if not skill_name:
                continue
            parsed = _parse_skill_prompt(prompt_file)
            collisions.setdefault(skill_name, []).append(f"{source.source_ref}:{prompt_file}")
            discovered[skill_name] = DiscoveredSkill(
                skill_name=skill_name,
                name=parsed["name"] or skill_name,
                description=parsed["description"],
                source_kind=source.source_kind,
                source_path=str(skill_dir),
                prompt_file=str(prompt_file),
                metadata={
                    "label": source.label,
                    "relative_path": relative_parent,
                },
            )
    conflicts = [
        SkillDiscoveryConflict(
            conflict_kind="duplicate_skill_name",
            skill_name=skill_name,
            sources=entries,
            message=f"Skill '{skill_name}' was discovered from multiple sources; the last scanned version is currently selected.",
        )
        for skill_name, entries in collisions.items()
        if len(entries) > 1
    ]
    return {
        "skills": sorted(discovered.values(), key=lambda item: item.skill_name),
        "conflicts": sorted(conflicts, key=lambda item: item.skill_name),
    }


def _parse_skill_prompt(prompt_file: Path) -> dict[str, str]:
    text = prompt_file.read_text(encoding="utf-8")
    frontmatter: dict[str, str] = {}
    body = text
    match = _FRONTMATTER_PATTERN.match(text)
    if match:
        for raw_line in match.group(1).splitlines():
            line = raw_line.strip()
            if not line or ":" not in line:
                continue
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip().strip('"').strip("'")
        body = text[match.end() :]
    description = frontmatter.get("description", "").strip()
    if not description:
        description = _first_body_paragraph(body)
    return {
        "name": frontmatter.get("name", "").strip(),
        "description": description,
    }


def _first_body_paragraph(body: str) -> str:
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", body) if item.strip()]
    for paragraph in paragraphs:
        if paragraph.startswith("#"):
            continue
        return " ".join(line.strip() for line in paragraph.splitlines())
    return ""
