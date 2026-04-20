from __future__ import annotations

from dataclasses import dataclass

from core.contracts import ExecutionContext, NodeExecutionResult
from core.state.models import PolicyAction, PolicyDecisionRecord, SideEffectRecord
from core.tools.models import ToolApprovalMode, ToolDescriptor, ToolInvocationRequest

from .skill_prompt_service import resolve_active_skill_packages


@dataclass
class SkillRuntimePolicyEngine:
    policy_name: str = "skill_runtime_policy"

    def pre_node_execute(self, context: ExecutionContext) -> PolicyDecisionRecord:
        return self._decision(
            context=context,
            action=PolicyAction.ALLOW,
            reason_code="skill_node_allowed",
            reason_message="node execution allowed by skill runtime policy",
        )

    def pre_tool_invoke(
        self,
        descriptor: ToolDescriptor,
        request: ToolInvocationRequest,
        context: ExecutionContext,
    ) -> PolicyDecisionRecord:
        runtime_resource_context = (
            context.agent_binding.metadata.get("runtime_resource_context", {})
            if context.agent_binding is not None
            else {}
        )
        resolved = resolve_active_skill_packages(
            runtime_resource_context if isinstance(runtime_resource_context, dict) else {},
            dict(context.selected_input),
        )
        active_skills = [
            item
            for item in resolved["active"]
            if isinstance(item, dict) and item.get("execution_mode") == "human_confirmed"
        ]
        if active_skills and _tool_requires_human_confirmation(descriptor):
            skill_names = [
                str(item.get("skill_name", "")).strip()
                for item in active_skills
                if str(item.get("skill_name", "")).strip()
            ]
            return self._decision(
                context=context,
                action=PolicyAction.REQUIRE_APPROVAL,
                reason_code="skill_human_confirmation_required",
                reason_message=(
                    f"tool '{descriptor.tool_ref}' requires approval because active skills "
                    f"{', '.join(skill_names)} are configured as human_confirmed"
                ),
                metadata={
                    "tool_ref": descriptor.tool_ref,
                    "active_skill_names": skill_names,
                    "execution_mode": "human_confirmed",
                },
            )
        return self._decision(
            context=context,
            action=PolicyAction.ALLOW,
            reason_code="skill_tool_allowed",
            reason_message=f"tool '{descriptor.tool_ref}' allowed by skill runtime policy",
            metadata={
                "tool_ref": descriptor.tool_ref,
                "active_skill_names": [
                    str(item.get("skill_name", "")).strip()
                    for item in resolved["active"]
                    if isinstance(item, dict) and str(item.get("skill_name", "")).strip()
                ],
            },
        )

    def pre_side_effect(
        self, context: ExecutionContext, side_effect: SideEffectRecord
    ) -> PolicyDecisionRecord:
        return self._decision(
            context=context,
            action=PolicyAction.ALLOW,
            reason_code="skill_side_effect_allowed",
            reason_message="side effect allowed by skill runtime policy",
            metadata={"target_ref": side_effect.target_ref},
        )

    def post_node_execute(
        self, context: ExecutionContext, result: NodeExecutionResult
    ) -> PolicyDecisionRecord | None:
        return None

    def _decision(
        self,
        *,
        context: ExecutionContext,
        action: PolicyAction,
        reason_code: str,
        reason_message: str,
        metadata: dict[str, object] | None = None,
    ) -> PolicyDecisionRecord:
        services = context.services
        decision_id = (
            services.id_generator.new("policy")
            if services is not None and services.id_generator is not None
            else f"policy_{context.run_record.run_id}_{context.node_state.node_id}_{reason_code}"
        )
        return PolicyDecisionRecord(
            decision_id=decision_id,
            run_id=context.run_record.run_id,
            node_id=context.node_state.node_id,
            action=action,
            policy_name=self.policy_name,
            reason_code=reason_code,
            reason_message=reason_message,
            metadata=metadata or {},
        )


def _tool_requires_human_confirmation(descriptor: ToolDescriptor) -> bool:
    if descriptor.approval_mode == ToolApprovalMode.REQUIRED:
        return True
    if str(descriptor.side_effect_kind) != "read_only":
        return True
    tool_kind = str(descriptor.metadata.get("tool_kind", "")).strip().lower()
    if tool_kind in {"shell"}:
        return True
    return False
