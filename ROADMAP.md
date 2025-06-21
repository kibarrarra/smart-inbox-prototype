# Smart‑Inbox — Roadmap

_Last updated: 2025‑06‑10_

| Phase | Key Outcomes | Issues / IDs | Target |
|-------|--------------|--------------|--------|
| **1 Prototype Hardening** | JSON‑schema prompt, secret manager, atomic state, PII‑safe logs. | C‑1 … C‑6 | July 2025 |
| **2 Learning Loop** | `/feedback`, FAISS K‑NN, nightly stats dashboard. | C‑7 C‑8 C‑10 | Aug 2025 |
| **3 User Value Add** | Digest generator, Slack alerting, draft replies (stretch). | C‑9 | Sept 2025 |
| **4 Scale & Multi‑Provider** | OutlookProvider, Terraform Cloud Run, autoscale tests @100 QPS. | C‑11 C‑12 | Q4 2025 |
| **5 On‑Prem Fine‑Tune** | MiniLM LoRA nightly job, RTX‑class GPU deploy, >10 pp F1 gain. | C‑13 | 2026 |

## Guiding Principles
1. **Don’t lose a single critical e‑mail—ever.** Precision may be 99 %, recall must be 100 %.
2. **Everything asynchronous.** Pub/Sub ack < 250 ms → background queue.
3. **Reproducible infra** (Terraform) before adding teammates.
4. **Zero vendor lock‑in.** Swap OpenAI out without touching business logic.

