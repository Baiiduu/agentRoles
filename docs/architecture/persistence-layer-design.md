# Persistence Layer Design

## Goal

Build a durable persistence layer for the agent platform so that all configurable data can be stored consistently, queried safely, and extended without rewriting the storage model when new features such as skills, workflow bindings, approval rules, or domain-pack assets are added.

## Current State Review

The project already persists part of its configuration, but the storage model is split by page-level concern instead of domain entity:

- `runtime_data/agent_configs.json`
- `runtime_data/agent_capabilities.json`
- `runtime_data/agent_resource_registry.json`
- `runtime_data/education/*.json` legacy compatibility files

This works for a prototype, but it has four structural limits:

1. Agent configuration is split across multiple JSON files and re-joined at runtime.
2. The schema is implicit in Python dataclasses instead of versioned centrally.
3. New configuration domains such as skills or workflow policies will likely create more sibling JSON files.
4. Cross-entity queries are awkward, for example:
   agent -> assigned MCP servers -> enabled tools -> workspace -> effective capability surface.

## Recommended Storage Strategy

Use a layered approach:

1. **Repository interfaces in application/core**
   Keep the current facade/service structure, but make storage depend on repository contracts instead of JSON files directly.
2. **SQLite as the default local persistence engine**
   Good fit for the current single-user/local-console product stage.
   Easy migration from JSON.
   Strong enough for filtering, joins, migrations, and transactional writes.
3. **Relational core + JSON extension fields**
   Put stable identifiers and query-heavy fields into columns.
   Put future-facing, pack-specific, or not-yet-stable fields into `json` text columns.

This gives you strong structure now without blocking future incomplete modules like skills.

## Why SQLite First

- Better than pure JSON for multi-entity consistency.
- Much cheaper than introducing PostgreSQL before the product needs deployment-grade infra.
- Easy to keep an export/import bridge to existing JSON runtime snapshots.
- Future upgrade path is straightforward because the repository layer can swap SQLite for PostgreSQL later.

## Target Architecture

Suggested layers:

- `core/persistence/contracts.py`
  Repository interfaces.
- `infrastructure/persistence/sqlite/`
  SQLAlchemy or `sqlite3` implementation, migrations, row mappers.
- `application/...`
  Existing facades keep orchestrating config/capability/resource composition.
- `runtime_data/`
  Keep only runtime logs, cache, exports, and migration snapshots.

## Persistence Boundaries

Separate **static registration** from **mutable runtime configuration**.

### 1. Static registration

These still come from code and domain packs:

- agent descriptors
- tool descriptors
- workflow definitions
- domain pack metadata

They are the platform baseline.

### 2. Mutable persisted configuration

These should go into the persistence layer:

- agent config
- agent capability
- agent resource bindings
- skill registry
- workflow binding / workflow config
- workspace root and per-agent workspace registration
- MCP server registry
- pack-scoped extension config

## Recommended Data Model

### `domain_packs`

Stores pack-level metadata so the UI and future configuration panels can query pack structure without scanning Python code only.

Core fields:

- `pack_id`
- `name`
- `version`
- `summary`
- `owner`
- `maturity`
- `metadata_json`

### `agents`

Stable catalog row for each registered agent.

Core fields:

- `agent_id`
- `pack_id`
- `name`
- `role`
- `description`
- `version`
- `enabled`
- `descriptor_json`

`descriptor_json` preserves future descriptor fields without schema churn.

### `agent_configs`

Prompt and model-related mutable config.

Core fields:

- `agent_id`
- `llm_profile_ref`
- `system_prompt`
- `instruction_appendix`
- `response_style`
- `quality_bar`
- `enabled`
- `metadata_json`
- `updated_at`

### `agent_capabilities`

Agent policy and execution surface overrides.

Core fields:

- `agent_id`
- `enabled`
- `approval_mode`
- `handoff_mode`
- `metadata_json`
- `updated_at`

### `agent_capability_tool_refs`

- `agent_id`
- `tool_ref`

### `agent_capability_memory_scopes`

- `agent_id`
- `memory_scope`

### `agent_capability_policy_profiles`

- `agent_id`
- `policy_profile`

### `agent_mcp_bindings`

- `agent_id`
- `server_ref`
- `enabled`
- `usage_notes`
- `tool_refs_json`

### `skills`

Registry of known skills.

Core fields:

- `skill_name`
- `name`
- `description`
- `enabled`
- `notes`
- `trigger_kinds_json`
- `metadata_json`

### `agent_skill_bindings`

- `agent_id`
- `skill_name`
- `enabled`
- `scope`
- `execution_mode`
- `trigger_kinds_json`
- `usage_notes`
- `metadata_json`

This is the key table for future extensibility.
When skill execution rules evolve, most new fields can first land in `metadata_json`.

### `mcp_servers`

- `server_ref`
- `name`
- `description`
- `connection_mode`
- `transport_kind`
- `command`
- `args_json`
- `endpoint`
- `env_json`
- `cwd`
- `enabled`
- `notes`
- `tool_refs_json`
- `discovered_tool_refs_json`
- `metadata_json`

### `workspace_roots`

- `workspace_root_id`
- `root_path`
- `enabled`
- `provisioned`
- `notes`

### `agent_workspaces`

- `agent_id`
- `workspace_root_id`
- `relative_path`
- `absolute_path_cache`
- `enabled`
- `notes`

### `workflow_configs`

Reserve this now even if workflow customization is not finished.

- `workflow_id`
- `pack_id`
- `enabled`
- `config_json`
- `metadata_json`

### `agent_workflow_bindings`

- `agent_id`
- `workflow_id`
- `enabled`
- `binding_mode`
- `config_json`

### `pack_extensions`

Generic escape hatch for unfinished modules.

- `extension_id`
- `pack_id`
- `owner_type`
- `owner_id`
- `extension_kind`
- `config_json`
- `updated_at`

This lets future modules persist pack-specific config without immediately forcing a schema redesign.

## Configuration Composition Rule

At runtime, compose final agent state in this order:

1. code-defined descriptor baseline
2. persisted pack metadata
3. persisted agent config
4. persisted capability overrides
5. persisted resource bindings
6. runtime-discovered MCP tool surface

This matches the way the current runtime already merges descriptor, config, capability, and resource manager state, but gives each layer a stable storage owner.

## Extensibility Rules

To avoid future persistence rewrites, follow these rules:

1. Every new configurable feature must declare its owner entity.
   Example: skill binding belongs to `agent_skill_bindings`, not a random `metadata` blob on another table.
2. Every table may keep one `metadata_json` field for non-query-heavy experimental fields.
3. Query-heavy fields must be promoted to first-class columns.
4. No new top-level JSON file for mutable config unless it is an export/import artifact.
5. Runtime cache and durable config must be separated.

## Migration Plan

### Phase 1

Introduce repository interfaces and keep current JSON repositories as compatibility adapters.

### Phase 2

Add SQLite repositories and migration scripts:

- import `agent_configs.json`
- import `agent_capabilities.json`
- import `agent_resource_registry.json`
- import legacy `runtime_data/education/*.json`

### Phase 3

Switch facades to a unified persistence provider factory.

### Phase 4

Keep JSON only for:

- exports
- backups
- logs
- discovered cache snapshots if desired

## Suggested First Implementation Slice

If you want the least risky start, implement in this order:

1. `agents`
2. `agent_configs`
3. `agent_capabilities`
4. `mcp_servers`
5. `skills`
6. `agent_mcp_bindings`
7. `agent_skill_bindings`
8. `workspace_roots`
9. `agent_workspaces`

That sequence covers almost every config surface already visible in the current UI.

## UI Implication

The playground agent selector should consume a tree-shaped payload derived from persisted pack/agent structure, not infer grouping only in the browser.

Recommended future API shape:

- `agent_tree`
- `pack_tree`
- `config_nodes`

This makes it easy later to show:

- `domain_packs / education / agents / ...`
- `domain_packs / education / workflows / ...`
- `domain_packs / education / skills / ...`

without reworking the frontend navigation model again.

## Final Recommendation

Use **SQLite + repository abstraction + relational core tables + JSON extension columns**.

This is the best fit for the project's current maturity:

- enough structure for all configs to be durable
- enough flexibility for unfinished skill/workflow modules
- easy migration from current JSON files
- easy upgrade later to PostgreSQL if the platform becomes multi-user or server-hosted
