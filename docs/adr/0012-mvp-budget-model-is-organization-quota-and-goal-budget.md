# MVP budget model is Organization Quota and Goal Budget

MVP budget enforcement has two controls: an Organization Quota for the platform-wide token spending ceiling, and a Goal Budget for each Goal Run. Department and Digital Employee token usage are analytics dimensions, not independent blocking quotas in the MVP.

This supersedes ADR-0006's Department Quota and Digital Employee Quota model. The simpler model keeps the two controls that stop the most important failure modes: Organization Quota prevents platform-wide cost runaway, while Goal Budget prevents one delegated Goal from expanding across many employees and consuming unbounded tokens. Token Ledger still records employee, department, goal, and work-item dimensions so department or employee budgets can be added later if real operations need them.

The Platform still avoids speculative token pre-deduction. It checks whether Organization Quota or Goal Budget is already exceeded before starting a model-cost call, records provider-reported usage after the call, and uses settled usage for the next enforcement decision. Work Item usage is tracked for analytics and debugging, but Work Item Budget is not a user-facing MVP control.
