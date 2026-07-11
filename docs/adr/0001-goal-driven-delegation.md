# Goal-driven delegation over preset DAG orchestration

Status: superseded by ADR-0010.

The original technical design (start.md) assumed multi-Agent collaboration would be driven by a WorkflowEngine executing predefined DAGs — an administrator designs the flow, and employees execute steps in order.

We decided to replace that with **goal-driven delegation**: a human assigns a Goal to one Digital Employee, who owns its completion end-to-end. That employee decomposes the goal, queries the Employee Directory for colleagues with matching Skills and availability, and delegates subtasks dynamically. There is no preset DAG; the collaboration graph emerges at runtime.

**Why**: real enterprise workflows are not assembly lines. A manager doesn't draw a flowchart before asking their team to do work — they assign a goal and trust the team to figure out who does what. Digital employees that wait for a DAG to tell them what to do are automations, not employees. Digital employees that self-organize around goals behave like the team members they're meant to be.

**Consequences**: the WorkflowEngine shrinks from a core orchestration component to an optional lightweight coordinator. The InstanceManager gains delegation primitives. The Employee Directory becomes a critical runtime dependency — without it, employees cannot discover whom to delegate to.
