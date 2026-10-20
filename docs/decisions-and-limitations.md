# Architectural Decisions, Scope, & Limitations

## 1. Architectural Decisions

### ADR-01: Modular Team Ownership & Separation of Concerns
* **Context**: A 3-person engineering team requires strict independent deliverables with decoupled interfaces.
* **Decision**: Automation (Team Lead), Backend (Member 1), and Frontend (Member 2) communicate via shared schemas and REST endpoints.
* **Benefit**: Members can test and mock their components without waiting for synchronous availability of other modules.

### ADR-02: Deterministic Baseline via Seeded Defects
* **Context**: Visual AI testing requires reproducible test cases to benchmark VLM accuracy across runs.
* **Decision**: Instead of testing random external websites, we maintain a dedicated mock e-commerce store (`app-under-test`) with 3 deterministic visual bugs in `src/styles/defects.css`.
* **Benefit**: Produces pixel-identical before-and-after evidence every run.

### ADR-03: Abstract VLM Adapter with Deterministic Mock
* **Context**: Real multimodal VLM API calls (GPT-4o, Claude 3.5 Sonnet) incur latency, cost, and quota constraints during local unit testing.
* **Decision**: All model interactions are mediated by a unified `VLMAdapter` interface with a deterministic `MockVLMAdapter` fallback.
* **Benefit**: Complete pipeline tests can execute locally in milliseconds without API keys.

### ADR-04: Bounded Self-Healing Retries
* **Context**: Self-healing loops risk infinite recursive repair cycles if an AI patch fails to resolve a bug.
* **Decision**: Maximum repair attempts are capped at **1 retry**. If the retest fails or confidence is ambiguous, the run transitions to `needs_review` for human oversight.

---

## 2. Scope Boundaries: MVP vs. Stretch Goals

| Capability | MVP (Phase 1–2) | Stretch Goal (Phase 3–4) |
|---|---|---|
| **Target Web App** | One mock React e-commerce application | Arbitrary multi-tenant production websites |
| **Tested Flows** | Products &rarr; Cart &rarr; Checkout journey | Dynamic, arbitrary user paths |
| **Viewports** | 4 standard viewports (2 desktop, 2 mobile) | Continuous responsive breakpoint sweeps |
| **Patch Scope** | Constrained CSS style files | Full-stack JavaScript and component refactoring |
| **PR Merge** | Human QA approval required | Autonomous CI/CD merge and deployment |

---

## 3. Known Limitations

1. **In-Memory Backend Store**: The development backend uses an in-memory run registry (`fake_runs_db`). Persistent Postgres/SQLite storage is deferred to Phase 4.
2. **Local Host Target**: The runner targets local or pre-configured staging instances. Arbitrary external hosts are restricted by security policy.
3. **Single Active Run**: Concurrent multi-run execution is queued sequentially to prevent Playwright port collisions.
