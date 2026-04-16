"""Backward-compatible console interface aliases."""

from interfaces.http_console import ProjectConsoleService


EducationConsoleService = ProjectConsoleService

__all__ = ["EducationConsoleService", "ProjectConsoleService"]
