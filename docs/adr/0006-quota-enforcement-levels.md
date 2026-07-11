# Quota enforcement differs by level

Status: superseded by ADR-0012.

Organization Quota is a hard quota, Department Quota is soft by default, and Digital Employee Quota is controlled by policy.

**Why**: Organization Quota represents platform-level cost or account risk and must prevent runaway spending. Department Quota is an operational management signal; stopping an entire department during a business spike could create a larger incident. Digital Employee behavior varies by role, so employee-level enforcement needs policy control.

**Consequences**: approaching quota thresholds emits warnings and does not slow work. Organization overage blocks new high-cost runtime calls. Department overage creates management alerts by default. Digital Employee overage may either alert or mark that employee `quota_blocked` depending on the configured Quota Policy.

The MVP enforces only Daily Token Quota, reset by natural day in the platform timezone. Monthly token usage is tracked for KPI and reporting, but monthly quota does not participate in hard blocking or employee stopping in the MVP.

Quota settlement uses provider-reported token usage after the model call. Before a request starts, Platform only checks whether the relevant quota is already exceeded; it does not reserve or deduct estimated tokens. If a provider does not return usage, Platform records an estimated usage entry with `estimated=true`. Enforcement decisions are based on settled usage, not speculative pre-deduction.

Organization hard quota overage blocks only data-plane calls that can create new model cost: Digital Employee LLM calls, answer generation after knowledge retrieval, and autonomous/delegated task execution. It does not block control-plane actions such as admin login, viewing status and Token Ledger, stopping employees, writing audit logs, sending alerts, or adjusting quotas. The control plane must stay available so administrators can investigate and stop loss after an overage.

When a Digital Employee hard quota is exceeded, Platform marks the employee `quota_blocked` and rejects new model-cost calls for that employee. Platform does not kill the Hermes Instance as the default action. Keeping the instance alive preserves diagnostic context and allows administrators to inspect status, stop the employee explicitly, adjust quota, or recover the employee without losing runtime evidence.

Hermes Agent already reports per-run token usage through its API responses and events. Platform records those Hermes usage values into its own Token Ledger and treats the Platform ledger as the quota source of truth. Hermes internal session counters and session DB are useful runtime telemetry, but they are not the Platform quota ledger.
