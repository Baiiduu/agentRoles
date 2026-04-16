import type { AgentCapabilityDto, CapabilityValidationResult } from "../types/agentCapability";

export function validateCapability(capability: AgentCapabilityDto): CapabilityValidationResult {
  const messages: string[] = [];

  const mcpServers = capability.mcp_bindings
    .map((item) => item.server_ref.trim())
    .filter(Boolean);
  if (new Set(mcpServers).size !== mcpServers.length) {
    messages.push("MCP server_ref contains duplicates");
  }

  const skills = capability.skill_bindings
    .map((item) => item.skill_name.trim())
    .filter(Boolean);
  if (new Set(skills).size !== skills.length) {
    messages.push("skill_name contains duplicates");
  }

  for (const binding of capability.mcp_bindings) {
    if (binding.enabled && !binding.server_ref.trim()) {
      messages.push("enabled MCP binding requires server_ref");
    }
  }

  for (const binding of capability.skill_bindings) {
    if (binding.enabled && !binding.skill_name.trim()) {
      messages.push("enabled skill binding requires skill_name");
    }
  }

  if (!["none", "human_review", "required"].includes(capability.approval_policy.mode)) {
    messages.push("approval mode is invalid");
  }

  if (!["manual", "guided", "blocked"].includes(capability.handoff_policy.mode)) {
    messages.push("handoff mode is invalid");
  }

  return {
    valid: messages.length === 0,
    messages,
  };
}
