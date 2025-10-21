# LiveKit-Agent Documentation Index

## How to Navigate
- Start here before touching the codebase to understand current architecture and available references.
- Review **System/** for technical deep dives, **Tasks/** for feature-specific PRDs or plans, and **SOP/** for repeatable workflows.
- Keep this index updated whenever you add, remove, or rename documentation files.

## Directory Guide
- `System/` — authoritative description of the platform’s architecture, integrations, and runtime behaviour.
- `Tasks/` — feature requirements and implementation plans (create per feature; none documented yet).
- `SOP/` — step-by-step guides for common workflows (create on demand; currently empty).

## Document Summaries
- `System/project_architecture.md` — full-stack overview covering repository layout, runtime data flow between services, external dependencies (OpenAI, LiveKit, Deepgram, Silero), configuration expectations, and operational considerations.
- `SOP/update_livekit_agent_persona_and_tools.md` — step-by-step guide for editing the LiveKit agent persona, tool registry, and related documentation.
- `SOP/maintain_frontend_shadcn.md` — workflow for evolving the Tailwind + shadcn-based frontend, including verification and documentation steps.

## Maintenance Checklist
- After modifying services, update the relevant System or SOP files and ensure the new/changed documents are linked here.
- Archive deprecated documents under version control instead of deleting them outright to preserve history.
- Confirm `.env` examples and Docker compose references stay in sync with service-level documentation.

## Related Docs
- `AGENTS.md` — repository-wide documentation policy and folder expectations.
