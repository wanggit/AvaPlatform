# Job Template System Prompt maps to Hermes identity

Job Template System Prompt is the Platform-owned role identity for a Digital Employee. Because each Digital Employee maps to one Hermes Agent Instance and one Hermes Profile, Platform must render the published Job Template System Prompt into that employee's Hermes identity instead of sending it as an ordinary user message.

**Why**: Hermes supports system-level identity through two native mechanisms. First, `AIAgent` accepts `ephemeral_system_prompt`, stores it on the agent instance, and appends it to the effective system message before model API calls. Second, Hermes loads `SOUL.md` from `HERMES_HOME` as the primary identity slot in the cached system prompt; named Hermes profiles have their own `SOUL.md`. These mechanisms prove that Platform can support per-Digital-Employee System Prompt without modifying Hermes core.

**Evidence from Hermes 2026.6.19**:

- `run_agent.py` exposes `AIAgent(..., ephemeral_system_prompt=...)` and forwards it to `agent_init.init_agent`.
- `agent/agent_init.py` documents `ephemeral_system_prompt` as a system prompt used during agent execution and stores it as `agent.ephemeral_system_prompt`.
- `agent/conversation_loop.py` appends `agent.ephemeral_system_prompt` to the effective system prompt and sends it with `role: system` on API calls.
- `agent/system_prompt.py` defines the stable system prompt tier as including identity from `SOUL.md` or the default agent identity.
- `agent/prompt_builder.py` documents `SOUL.md` as the agent identity slot and loads it from `HERMES_HOME`.
- Hermes profile docs describe `~/.hermes/profiles/<name>/` as owning its own `SOUL.md` / `USER.md` identity.

**Consequences**: On Digital Employee creation, Platform creates or updates the employee's Hermes Profile and writes the published Job Template System Prompt into that profile's `SOUL.md`. When Platform needs a non-persistent runtime overlay, it may pass the same or augmented prompt through `ephemeral_system_prompt` while starting or calling the Hermes Instance.

Draft Job Template edits must not change running employees. Publishing a new Job Template Version computes the System Prompt diff and affected employee count. Active employees that inherit the template receive a Profile update; because Hermes caches the system prompt once per session, a System Prompt change requires a reload, new session, or Hermes Instance restart before it is guaranteed to take effect.

Employee-level configuration may disable or narrow inherited capabilities, but it must not append identity text that expands the published Job Template responsibilities, red lines, knowledge entitlement, or tool entitlement. Temporary task instructions belong in user/task messages, not in the persisted System Prompt.

Platform must audit System Prompt publication and rollout. Audit records should include template id, version, affected employee ids/count, prompt diff summary or hash, operator, timestamp, and rollout status. Full prompt text may be masked in normal list views if it contains sensitive operating instructions.
