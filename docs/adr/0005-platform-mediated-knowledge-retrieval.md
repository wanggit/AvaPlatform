# Knowledge retrieval is mediated by the Platform

Digital Employees will not call RAGFlow directly. Each Hermes Instance receives a Knowledge Retrieval Tool, exposed either as a Hermes tool or through an MCP server, and that tool calls the Platform Knowledge Adapter.

**Why**: Platform must enforce Job Template authorization, keep RAGFlow credentials out of employee Profiles, record retrieval logs and source citations, and preserve the ability to replace or add knowledge providers later without rewriting every Hermes Instance configuration.

**Consequences**: RAGFlow API keys are stored only in Platform-side Knowledge Connection configuration. Hermes Profiles receive only the Platform retrieval tool configuration and an Employee Service Token scoped to that Digital Employee runtime. Runtime retrieval requests include the Digital Employee identity; Platform validates the token, resolves the employee's Job Template, checks the authorized Knowledge Source set, calls RAGFlow through the adapter, and returns normalized hits with citations.

Employee Service Tokens are issued by Platform, bind to `employee_id` and the current Profile or Instance identity, and can be rotated or revoked when the employee is disabled, the Job Template changes, or the Hermes Instance is recreated. They grant access only to employee runtime endpoints such as `POST /api/v1/knowledge/retrieve`; they never contain RAGFlow credentials.

Knowledge retrieval responses must include normalized source citations and a Platform audit ID. The Platform may omit synthesized answers in the MVP, but it must return the matched content, source identity, document identity, chunk identity, score, citation string, and `audit_id` so humans and audit jobs can verify which enterprise knowledge was used.

In the MVP, Digital Employees inherit Knowledge Source access from their Job Template. Employee-level configuration may narrow that inherited set, but it may not grant additional Knowledge Sources outside the template. This keeps authorization auditable and makes retrieval behavior explainable by inspecting the Job Template first.

When a new Job Template Version is published, Knowledge Source changes automatically apply to active Digital Employees that inherit that template. Draft edits have no runtime effect. Publishing must show the affected employee count and record an audit event with the Knowledge Source diff. Employee-level narrowing still applies, but the final entitlement can never exceed the newly published template scope.

Knowledge Source entitlement changes do not require restarting Hermes Instances. The Knowledge Retrieval Tool must not cache the authorized source set; each retrieval request is authorized by Platform against the current published Job Template. Reload or restart is reserved for changes that alter Profile files or runtime configuration, such as Skill package updates, model configuration changes, or System Prompt changes.

Admin Knowledge Preview is separate from runtime retrieval. Administrators may preview one or more Knowledge Sources directly to validate configuration, without going through Job Template entitlements. Preview requests must still be authorized as admin actions and audited. Digital Employee runtime retrieval always uses Employee Service Tokens and Job Template entitlements.
