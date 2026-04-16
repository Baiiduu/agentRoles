from __future__ import annotations

from core.evaluation import EvaluationCase, EvaluationDriver, EvaluationExecution
from core.runtime import RuntimeService


class EducationEvaluationDriver(EvaluationDriver):
    """
    Domain-specific evaluation driver for education workflows.

    Education workflows currently accept entry input through
    `thread_state.global_context`, so this driver injects the case seed payload
    before the run starts without changing core runtime contracts.
    """

    def execute(self, runtime, case: EvaluationCase) -> EvaluationExecution:
        if not isinstance(runtime, RuntimeService):
            raise TypeError(
                "EducationEvaluationDriver requires RuntimeService because it "
                "must seed thread_state.global_context before run start"
            )

        thread = runtime.create_thread(
            case.thread_type,
            case.goal,
            title=case.title,
            owner_id=case.owner_id,
            tenant_id=case.tenant_id,
            metadata={
                **case.metadata,
                "evaluation_case_id": case.case_id,
            },
        )
        thread_state = runtime._deps.services.state_store.get_thread_state(thread.thread_id)
        if thread_state is None:
            raise ValueError(f"thread_state missing for '{thread.thread_id}'")

        global_context = case.trigger_payload.get("global_context", {})
        if not isinstance(global_context, dict):
            raise ValueError("education eval case trigger_payload.global_context must be a dict")
        thread_state.global_context = dict(global_context)
        runtime._deps.services.state_store.save_thread_state(thread_state)

        run = runtime.start_run(
            thread.thread_id,
            case.workflow_id,
            workflow_version=case.workflow_version,
            trigger=case.trigger,
            trigger_payload=dict(case.trigger_payload),
        )
        final_state = runtime.get_state(run.run_id)
        thread_record = runtime.get_thread(thread.thread_id)
        if thread_record is None:
            raise ValueError(f"thread '{thread.thread_id}' disappeared during evaluation")

        return EvaluationExecution(
            case=case,
            thread_record=thread_record,
            run_record=final_state.run_record,
            final_state=final_state,
            events=list(runtime.stream_events(final_state.run_record.run_id)),
            metadata={
                "domain": "education",
                "seeded_global_context_keys": sorted(global_context),
            },
        )
