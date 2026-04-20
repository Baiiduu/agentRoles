import type { RegisteredMCPServerDto } from "../../types/agentResourceManager";

export const emptyMcpServerForm: RegisteredMCPServerDto = {
  server_ref: "",
  name: "",
  description: "",
  connection_mode: "internal",
  transport_kind: "custom",
  command: "",
  args: [],
  endpoint: "",
  env: {},
  cwd: "",
  tool_refs: [],
  discovered_tool_refs: [],
  enabled: true,
  notes: "",
};

export const workspaceFilesystemPreset: RegisteredMCPServerDto = {
  server_ref: "filesystem.workspace",
  name: "Workspace Filesystem",
  description: "Allow an agent to list, read, search, and write files inside its workspace.",
  connection_mode: "internal",
  transport_kind: "custom",
  command: "",
  args: [],
  endpoint: "",
  env: {},
  cwd: "",
  tool_refs: ["fs.list_dir", "fs.read_file", "fs.write_file", "fs.make_dir", "fs.search_files"],
  discovered_tool_refs: [],
  enabled: true,
  notes: "Restricted to the current agent workspace directory.",
};

export function splitCsv(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function parseEnvLines(value: string) {
  const env: Record<string, string> = {};
  for (const line of value.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const index = trimmed.indexOf("=");
    if (index <= 0) continue;
    env[trimmed.slice(0, index).trim()] = trimmed.slice(index + 1).trim();
  }
  return env;
}

export function formatEnvLines(value: Record<string, string>) {
  return Object.entries(value)
    .map(([key, item]) => `${key}=${item}`)
    .join("\n");
}

export function capabilityCount(server: RegisteredMCPServerDto) {
  return server.tool_refs.length || server.discovered_tool_refs.length;
}
