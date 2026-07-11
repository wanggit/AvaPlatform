# Artifact Acceptance is separate from Approval

MVP treats Approval and Artifact Acceptance as different controls. Approval decides whether a high-risk action may proceed before execution; Artifact Acceptance decides whether a submitted result satisfies the Work Item or Goal acceptance criteria after execution.

This separation keeps business control clear. A Tool call can be approved and still produce a bad result, and an Artifact can be high quality even if no high-risk action required approval. Work Items therefore keep `submitted` and `accepted` as separate states, failed acceptance can move the item to `rework_required`, and acceptance outcomes feed KPI metrics such as first-pass acceptance rate, rework rate, and artifact adoption.
