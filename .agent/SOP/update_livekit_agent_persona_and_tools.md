# SOP: Update LiveKit Agent Persona and Tooling

## Purpose
Ensure consistent, testable updates when modifying the LiveKit agent's persona file or function-tool registry. Follow this process whenever you change agent behaviour, add/remove tools, or adjust instructions.

## Prerequisites
- Local environment with repository dependencies installed (`uv` + frontend `npm` workspace).
- Access to the OpenAI/LiveKit environment variables defined in `services/livekit_agent/.env`.
- Understanding of LiveKit Agents `@function_tool` semantics (name/description fallback to the function name/docstring).

## Steps
1. **Review Current Documentation**  
   - Read `.agent/System/project_architecture.md` for the latest agent structure overview.  
   - Open `services/livekit_agent/src/personality.md` to understand existing persona guidance.  
   - Inspect `services/livekit_agent/src/tools/registry.py` to see the current tool inventory and signatures.

2. **Plan the Change**  
   - Decide whether the update affects persona text, existing tools, or new tools.  
   - For new tools, sketch the desired input/output and any required external dependencies.  
   - Confirm naming conventions; the `@function_tool` decorator infers the tool name from the function identifier and the description from its docstring—no manual overrides needed.

3. **Edit Persona or Tools**  
   - Persona updates: edit `services/livekit_agent/src/personality.md`, keeping prose concise and behaviour-focused.  
   - Tool updates: modify or add functions in `services/livekit_agent/src/tools/registry.py`.  
     - Do **not** pass `name` or `description` overrides to `@function_tool`; the decorator must infer the name from the function identifier and the description from its docstring.  
     - Include a clear docstring because it surfaces verbatim as the tool description.  
     - Validate argument names to match what the LLM should call.  
     - If introducing async side effects (network/file I/O), guard with try/except and propagate friendly error messages.

4. **Synchronise Agent Entrypoint**  
   - Check `services/livekit_agent/src/agent/main.py` to ensure new tools are imported via `build_agent_tools`.  
   - Update any persona-dependent logic (e.g., language detection, status updates) if the change alters tool usage patterns.

5. **Run Quick Verification**  
   - Execute `python -m compileall services/livekit_agent/src/agent services/livekit_agent/src/tools` to catch syntax errors.  
   - Launch the worker (`uv run livekit-backend`) and perform a smoke test: join a room, trigger the tool, and confirm expected behaviour and citations.  
   - Tail logs for tool call errors or missing descriptions.

6. **Update Frontend & Docs If Needed**  
   - Adjust `frontend` components when persona/tool changes affect UI hints (e.g., knowledge sidebar).  
   - Document any new configuration (env vars, feature flags) in `.agent/System/project_architecture.md` and `frontend/.env.example` if applicable.

7. **Record the Change**  
   - Update `.agent/README.md` to include new or renamed documents.  
   - Summarise the change in PR notes, highlighting persona/tool impacts and validation performed.

## Verification Checklist
- [ ] Persona file updated with final copy.  
- [ ] Tool functions include accurate docstrings and handle error cases.  
- [ ] `python -m compileall` passes for agent/tool packages.  
- [ ] Live session smoke test confirms tool execution path.  
- [ ] Documentation and env examples reflect new behaviour.

## Related Docs
- `.agent/System/project_architecture.md`
- `services/livekit_agent/src/personality.md`
- `services/livekit_agent/src/tools/registry.py`
