from __future__ import annotations

from dataclasses import dataclass, field

from core.contracts import ExecutionContext, NodeExecutionResult, PolicyEngine
from core.state.models import PolicyAction, PolicyDecisionRecord, SideEffectRecord
from core.tools.models import ToolDescriptor, ToolInvocationRequest


@dataclass
class StaticPolicyEngine:
    """
    Reference policy engine for tests and local development.

    It keeps policy logic out of runtime while making allow/deny/approval
    behavior concrete enough for end-to-end verification.
    """

    deny_tool_refs: set[str] = field(default_factory=set)
    approval_tool_refs: set[str] = field(default_factory=set)
    redact_tool_refs: dict[str, list[str]] = field(default_factory=dict)
    deny_side_effect_targets: set[str] = field(default_factory=set)
    approval_side_effect_targets: set[str] = field(default_factory=set)
    policy_name: str = "static_policy"

    def pre_node_execute(self, context: ExecutionContext) -> PolicyDecisionRecord:
        return self._decision(
            context=context,
            action=PolicyAction.ALLOW,
            reason_code="node_allowed",
            reason_message="node execution allowed",
        )

    def pre_tool_invoke(
        self,
        descriptor: ToolDescriptor,
        request: ToolInvocationRequest,
        context: ExecutionContext,
    ) -> PolicyDecisionRecord:
        if descriptor.tool_ref in self.deny_tool_refs:
            return self._decision(
                context=context,
                action=PolicyAction.DENY,
                reason_code="tool_denied",
                reason_message=f"tool '{descriptor.tool_ref}' denied by policy",
            )
        if descriptor.tool_ref in self.approval_tool_refs:
            return self._decision(
                context=context,
                action=PolicyAction.REQUIRE_APPROVAL,
                reason_code="tool_requires_approval",
                reason_message=f"tool '{descriptor.tool_ref}' requires approval",
            )
        if descriptor.tool_ref in self.redact_tool_refs:
            return self._decision(
                context=context,
                action=PolicyAction.REDACT,
                reason_code="tool_input_redacted",
                reason_message=f"tool '{descriptor.tool_ref}' input redacted by policy",
                redactions=self.redact_tool_refs[descriptor.tool_ref],
            )
        return self._decision(
            context=context,
            action=PolicyAction.ALLOW,
            reason_code="tool_allowed",
            reason_message=f"tool '{descriptor.tool_ref}' allowed",
        )

    def pre_side_effect(
        self, context: ExecutionContext, side_effect: SideEffectRecord
    ) -> PolicyDecisionRecord:
        if side_effect.target_ref in self.deny_side_effect_targets:
            return self._decision(
                context=context,
                action=PolicyAction.DENY,
                reason_code="side_effect_denied",
                reason_message=f"side effect '{side_effect.target_ref}' denied by policy",
            )
        if side_effect.target_ref in self.approval_side_effect_targets:
            return self._decision(
                context=context,
                action=PolicyAction.REQUIRE_APPROVAL,
                reason_code="side_effect_requires_approval",
                reason_message=f"side effect '{side_effect.target_ref}' requires approval",
            )
        return self._decision(
            context=context,
            action=PolicyAction.ALLOW,
            reason_code="side_effect_allowed",
            reason_message="side effect allowed",
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
        redactions: list[str] | None = None,
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
            redactions=list(redactions or []),
            metadata={"tool_node_id": context.node_state.node_id},
        )
