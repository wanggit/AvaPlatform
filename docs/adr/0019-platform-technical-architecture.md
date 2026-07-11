# Platform technical architecture starts as a modular monolith

Status: accepted.

The Platform backend starts as a FastAPI modular monolith with separate worker processes. PostgreSQL is the source-of-truth database, Redis provides queue/cache/lock primitives, and MinIO or another S3-compatible object store keeps Skill packages, imported files, artifacts, and audit evidence.

This is intentionally not a microservice architecture in the first implementation. Job Templates, Digital Employees, Goals, Approvals, Tools, Knowledge, Budgets, Audit, and Metrics are tightly connected at this stage. Splitting them into services before the domain contracts stabilize would add distributed transactions, event ordering, deployment, and debugging complexity without a clear payoff.

Platform API owns control-plane behavior. Platform Workers own asynchronous work such as Employee Rollout Jobs, Hermes Profile rendering, Hermes Instance smoke tests, knowledge sync, approval continuation, budget aggregation, and audit rule evaluation. Hermes remains the execution runtime for each Digital Employee and is integrated through per-employee Profiles plus Hermes runtime APIs. RAGFlow remains an external knowledge system accessed through the Platform Knowledge Adapter.

Development environments should use Platform-owned PostgreSQL, Redis, and MinIO containers with project-specific ports and volumes. They should not implicitly reuse another local project's database, Redis, or RAGFlow's internal middleware. Existing local RAGFlow can be used as an external service through `RAGFLOW_BASE_URL` and `RAGFLOW_API_KEY`.

Model access is handled through Model Configuration records. The current development baseline uses an OpenAI-compatible LLM configuration, local Ollama for Embedding, and `RERANK_ENABLED=false` until a Rerank model is introduced. Secrets must stay in local `.env` files or deployment environment variables; repository files should only contain placeholders.

Consequences: module boundaries should be explicit in code, but all first-phase modules can share one process, one database, and one transaction boundary where needed. Service extraction is deferred until a module has stable contracts, independent scaling needs, or separate operational ownership.
