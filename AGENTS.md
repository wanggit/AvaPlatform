# AI 数字员工平台

## 工作区结构

- `hermes-agent-2026.6.19/` — Hermes Agent 上游源码，**只读**。仅在需要查阅 Hermes Agent 内部实现时打开，**禁止修改此目录下的任何文件**。
- 其他所有目录和文件 — 本平台的开发工作区。

## Agent skills

### Issue tracker

Issues tracked as markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the five canonical labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout — one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
