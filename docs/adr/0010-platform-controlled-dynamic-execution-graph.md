# Platform-controlled dynamic execution graph

Goal-driven collaboration remains the product model, but free recursive delegation is not the default execution model. A Digital Employee may propose Delegation, yet Platform must authorize it, create structured Work Items, maintain the Goal Run Execution Graph, enforce Delegation Policy, and keep the Root Goal Owner responsible for the final result.

This supersedes ADR-0001's stronger claim that the collaboration graph simply emerges at runtime from employees self-organizing. The revised decision keeps the rejection of administrator-authored static DAGs, but adds a Platform-owned runtime graph so enterprise controls are enforceable: loop detection, depth and fan-out limits, budget checks, data-sharing checks, approval requirements, cancellation, retry, traceability, and recovery after process failure.

MVP should start with a single Orchestrator-Worker layer: the Root Goal Owner can delegate bounded Work Items to specialist employees, while assignees cannot redelegate by default. Deeper delegation can be enabled later through Delegation Policy only after budget accounting, artifact validation, trace, and recovery behavior are proven.
