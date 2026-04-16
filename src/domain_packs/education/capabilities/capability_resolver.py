from __future__ import annotations

from dataclasses import asdict

from core.agents import AgentDescriptor

from .capability_models import EducationAgentCapability


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


class EducationAgentCapabilityResolver:
    def resolve_preview(
        self,
        descriptor: AgentDescriptor,
        capability: EducationAgentCapability,
    ) -> dict[str, object]:
        mcp_tool_refs = _unique(
            [
                tool_ref
                for binding in capability.mcp_bindings
                if binding.enabled
                for tool_ref in binding.tool_refs
            ]
        )
        enabled_skills = [binding.skill_name for binding in capability.skill_bindings if binding.enabled]
        resolved_tool_refs = _unique(list(descriptor.tool_refs) + list(capability.tool_refs) + mcp_tool_refs)
        resolved_memory_scopes = _unique(
            list(descriptor.memory_scopes) + list(capability.memory_scopes)
        )
        resolved_policy_profiles = _unique(
            list(descriptor.policy_profiles) + list(capability.policy_profiles)
        )
        workspace = capability.metadata.get("workspace", {})
        workspace_relative_path = ""
        workspace_enabled = False
        if isinstance(workspace, dict):
            workspace_relative_path = str(workspace.get("relative_path", "")).strip()
            workspace_enabled = bool(workspace.get("enabled", False))
        approval_mode = capability.approval_policy.mode
        handoff_mode = capability.handoff_policy.mode
        usage_guidance: list[str] = []
        if not capability.enabled:
            usage_guidance.append("This agent capability is currently disabled for active case work.")
        if resolved_tool_refs:
            usage_guidance.append(
                f"Operational surface includes {len(resolved_tool_refs)} tool reference(s)."
            )
        if capability.mcp_bindings:
            usage_guidance.append(
                f"MCP access is configured through {len([binding for binding in capability.mcp_bindings if binding.enabled])} enabled server binding(s)."
            )
        if enabled_skills:
            usage_guidance.append(
                f"Skill support is available through {len(enabled_skills)} enabled skill binding(s)."
            )
        if workspace_enabled and workspace_relative_path:
            usage_guidance.append(
                f"Agent workspace is provisioned at '{workspace_relative_path}' for project-local file operations."
            )
        if approval_mode in {"human_review", "required"}:
            usage_guidance.append(
                "Human confirmation should be expected before sensitive or externally visible actions."
            )
        if handoff_mode == "guided":
            usage_guidance.append("Agent handoff should follow the configured target allowlist.")
        if handoff_mode == "blocked":
            usage_guidance.append("This agent should not be selected as the next manual handoff target.")

        attention_points: list[str] = []
        if not capability.enabled:
            attention_points.append("Capability disabled")
        if approval_mode == "required":
            attention_points.append("Requires explicit approval")
        elif approval_mode == "human_review":
            attention_points.append("Needs human review for selected actions")
        if handoff_mode == "guided" and capability.handoff_policy.allowed_targets:
            attention_points.append(
                f"Handoff limited to {len(capability.handoff_policy.allowed_targets)} target(s)"
            )
        elif handoff_mode == "blocked":
            attention_points.append("Manual handoff blocked")

        operational_summary = (
            "Ready for live case work."
            if capability.enabled
            else "Not ready for live case work until re-enabled."
        )
        collaboration_summary = (
            f"Approval mode: {approval_mode}; handoff mode: {handoff_mode}."
        )
        return {
            "agent_id": descriptor.agent_id,
            "resolved_tool_refs": resolved_tool_refs,
            "resolved_memory_scopes": resolved_memory_scopes,
            "resolved_policy_profiles": resolved_policy_profiles,
            "enabled_mcp_servers": [
                binding.server_ref for binding in capability.mcp_bindings if binding.enabled
            ],
            "enabled_skills": enabled_skills,
            "approval_policy": asdict(capability.approval_policy),
            "handoff_policy": asdict(capability.handoff_policy),
            "workspace": {
                "relative_path": workspace_relative_path,
                "enabled": workspace_enabled,
            },
            "operational_summary": operational_summary,
            "collaboration_summary": collaboration_summary,
            "usage_guidance": usage_guidance,
            "attention_points": attention_points,
        }
