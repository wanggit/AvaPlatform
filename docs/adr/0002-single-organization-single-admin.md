# Single-organization platform with one admin backend

The earlier product direction assumed a multi-tenant SaaS platform with a separate tenant admin backend and super admin backend. We decided to remove multi-tenancy from the product model and build a single-organization AI digital employee platform.

There is now one management backend. It contains both daily operations such as Digital Employee, Goal, Employee Directory, KPI, and Organization Chart management, and system configuration such as Job Template, Skill, Knowledge Base, model, quota, and audit rule management.

**Why**: the current product goal is to manage one organization's digital workforce, not operate a SaaS marketplace for many isolated tenants. Keeping Tenant, tenant template copying, tenant quotas, and cross-tenant audit creates product and implementation complexity that does not serve the immediate use case.

**Consequences**: Tenant is no longer a core domain concept. Job Template is a single global concept rather than Platform Job Template versus Tenant Job Template. Job Template can directly bind Department, Skill, Knowledge Source, tool whitelist, Red Line, model, and quota. The previous two-entry frontend prototype is merged into one admin backend. Any technical design that still describes tenant isolation, tenant IDs, tenant profile paths, or tenant-level quota is stale and should be rewritten before backend implementation.
