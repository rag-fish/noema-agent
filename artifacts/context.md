

# Context – noema-agent / Noesis Noema

This document is an **artifact for context rehydration**.

It is not a specification, not a roadmap, and not a promise of implementation.
Its sole purpose is to preserve *design intent*, *philosophical constraints*, and
*operational assumptions* that cannot be reliably retained across AI sessions.

This file is expected to be:
- Read manually by humans
- Re-ingested into LLM conversations when starting a new thread
- Updated deliberately, not frequently

---

## 1. Fundamental Positioning

- AI systems (including LLMs) **do not learn in-session nor across sessions**.
- They are **stateless probabilistic executors**, not responsible agents.
- Therefore, *memory, responsibility, and continuity* must be externalized into artifacts.

**Design consequence**:
> All long-lived intent must live in code, architecture, or artifacts — never in the AI.

---

## 2. Role of AI in This Project

AI is treated strictly as:
- A high-speed reasoning surface
- A language-based structure generator
- A thought expander and compressor

AI is **not**:
- A decision-maker
- A source of truth
- A holder of responsibility
- A reliable long-term collaborator

**Operational rule**:
> AI output is disposable unless explicitly crystallized into artifacts or code.

---

## 3. Core Architectural Philosophy

The system is intentionally split by **rate of change** and **responsibility**.

### Client Side (Noesis Noema app)
- Close to the human
- Fast iteration
- Holds policy, routing decisions, and UX logic
- Responsible for *choosing* where and how intelligence is invoked

### Server Side (noema-agent)
- On-demand, dockerized service
- Slow to change
- Executes given constraints without autonomous judgment
- Treats LLMs as replaceable execution engines

### Knowledge Assets (RAGpack)
- Model-agnostic
- May be used by client, server, or both
- Updated independently from code
- Considered *data*, not *logic*

**Invariant**:
> Components with different evolution speeds must never be tightly coupled.

---

## 4. Explicit Rejection of “Vibe Coding as a Goal”

Exploratory coding is acceptable.
Unstructured permanence is not.

- Goals must exist before implementation
- Architecture precedes optimization
- Complexity must be absorbed by structure, not intuition

**Key stance**:
> “Vibe coding” is a tool, not a methodology.
> Engineering requires intentional structure and historical traceability.

---

## 5. Artifact Strategy

Artifacts exist to compensate for AI’s lack of memory.

- Artifacts may be incomplete, informal, and opinionated
- Artifacts are not version-controlled as code
- Artifacts are allowed to decay and be rewritten

The `artifacts/` directory is intentionally:
- Git-ignored
- User-owned
- Session-bridging

**Purpose**:
> Provide a reproducible starting state for future reasoning,
> regardless of AI memory limitations.

---

## 6. Responsibility Model

- Responsibility always lies with the human initiator
- AI may assist but never commits
- Verification, UAT, and acceptance are mandatory human actions

**Non-negotiable**:
> Anything not verified by the human is considered untrusted.

---

## 7. Guiding Principle (Condensed)

> Do not ask AI to remember.
> Do not ask AI to decide.
> Do not ask AI to be responsible.
>
> Ask AI to help you think faster —
> then *freeze the result into artifacts you own*.

---

## End of Context