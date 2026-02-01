Noema Agent Engine (formerly LLM Document Agent)
===============================================

Overview
--------
Noema Agent Engine is the server-side agent and RAG execution engine of the Noesis Noema ecosystem.

It is designed as a privacy-first, OSS-first, Dockerized agent runtime that operates across on-premise, VPC, and cloud environments, acting as the *reasoning and orchestration core* behind Noesis Noema clients.

Rather than being a simple document Q&A service, Noema Agent Engine focuses on **Agentic RAG**:
- Iterative reasoning and retrieval loops
- Evidence-driven answer generation
- Explicit control over compute, cost, and privacy boundaries

This project is intentionally **not a SaaS**.
It is built for teams and enterprises that require:
- Full data ownership
- Deterministic deployment
- Transparent system behavior
- Long-term maintainability over rapid experimentation

In a typical architecture:
- **Noesis Noema (Client)** handles local interaction, lightweight inference, and user-facing reasoning traces
- **Noema Agent Engine (Server)** performs heavy retrieval, orchestration, evaluation, and multi-model routing
- **RAGpack** serves as the shared, portable knowledge unit between edge and server

Docker-based deployment ensures reproducibility, auditability, and infrastructure neutrality, enabling the same agent runtime to operate consistently across laptops, private servers, and cloud environments.

Architecture (Conceptual)
-------------------------
Noema Agent Engine is designed as part of an **Edge–Cloud Hybrid Agentic RAG architecture**, where responsibility is explicitly divided by capability, cost, latency, and privacy constraints.

At a high level, the system is composed of four logical layers:

1. Edge (Client)
   - Noesis Noema (macOS / iOS)
   - Local-first interaction and lightweight inference
   - Local RAGpack access and reasoning trace visualization
   - Acts as the entry point for user intent and constraints

2. Agent Core (Server)
   - Noema Agent Engine (this project)
   - Executes Agentic RAG loops (reason → retrieve → evaluate → refine)
   - Orchestrates retrieval, re-ranking, and evidence grounding
   - Enforces compute, cost, and privacy boundaries

3. Routing & Policy Layer
   - Determines whether execution occurs on:
     - Local models
     - On-prem / VPC-hosted models
     - External cloud LLM APIs
   - Decisions are based on:
     - Hardware profile
     - Network conditions
     - Privacy and cost policies
   - Supports graceful degradation when constraints cannot be satisfied

4. Knowledge Layer
   - RAGpack as a portable, versioned knowledge unit
   - Shared across edge and server environments
   - Supports text-first and multimodal extensions (image, video, audio metadata)


This separation allows the system to scale in capability without assuming unlimited compute, always-on connectivity, or unrestricted data sharing.

Design Principles
-----------------
Noema Agent Engine is guided by a small set of design principles that reflect the realities of 2026-era AI systems, not idealized infinite-compute environments.

1. Privacy-first by default
   - User and organizational data should never be forced to leave the environments they control.
   - External LLM APIs are always optional and explicitly governed by policy, not assumed.

2. OSS-first and self-hostable
   - Core functionality must remain usable with only open-source components and self-hosted infrastructure.
   - Commercial integrations (cloud LLMs, monitoring, etc.) are add-ons, not hard dependencies.

3. Deterministic, reproducible deployment
   - The same Docker-based setup should behave consistently across laptops, private servers, and cloud instances.
   - Configuration is declarative and versioned, enabling auditability and long-term maintainability.

4. Cost-aware reasoning and routing
   - Agentic RAG loops and test-time compute are treated as scarce resources, not infinite.
   - The router explicitly trades off latency, cost, and expected answer quality based on policy and context.

5. Evidence-driven Agentic RAG
   - Every answer should be traceable back to the retrieved evidence and the reasoning steps taken.
   - Reasoning traces and retrieval logs are first-class artifacts, not debugging afterthoughts.

6. Edge–Cloud independence
   - The system should not assume always-on connectivity or a specific hyperscaler.
   - Edge-only, on-prem-only, and hybrid deployments are all valid first-class configurations.

7. Composable, minimally coupled components
   - Retrieval, routing, reasoning, and evaluation are separated so they can evolve independently.
   - Noema Agent Engine is intended to be embedded into larger systems, not to be a monolith.

Prerequisites
-------------
- Docker Desktop (macOS/Windows/Linux)
- Docker Compose v2
- At least 16GB RAM recommended (minimum 8GB for small models)
- (Optional, for dev) git, curl, bash

Project Structure
-----------------
    .
    ├── app/
    │   └── web_ui.py
    ├── docker-compose.yml
    ├── Dockerfile
    ├── requirements.txt
    ├── README-dockerize.md
    └── (other supporting files/folders)

Quick Start
-----------
1. Clone the Repository

````````
git clone https://github.com/<your-repo>/LLM_Document_Agent.git
cd LLM_Document_Agent
````````

2. Build and Launch with Docker Compose (includes automatic Ollama model pull)

`````````
docker compose up --build
# or
docker-compose up --build
`````````

This starts both the 'ollama' LLM backend and the 'llm_streamlit' web frontend. The Ollama container automatically pulls the configured model during startup, so no manual intervention is needed.

3. Open the Web UI

Visit: http://localhost:8501

Advanced: Manual Model Pull (Optional)
--------------------------------------
If you prefer to manually pull or change models, you can enter the Ollama container and pull models yourself:

````````
docker ps
docker exec -it ollama bash
ollama pull llama3
# Replace "llama3" with any available model if desired
````````

After manual model pull, restart the Streamlit UI to apply changes:

````````
docker compose restart llm_streamlit
````````

Key Features
------------
- Detailed, context-rich answers thanks to advanced prompt engineering and RAG integration
- Fully local and private: No data leaves your machine—runs entirely via Docker & Ollama
- Production-ready, reproducible deployment: Any machine with Docker can instantly host the same environment
- Lightning fast: Llama3 provides state-of-the-art accuracy and speed for most use-cases
- Easy extensibility: Future backends (HuggingFace, LMStudio, vLLM) are planned

Known Issues / Troubleshooting
------------------------------
- Startup/Timeout: Wait for Ollama to fully load the model; 16GB+ RAM recommended for best performance
- CPU inference is slow: For best speed, use GPU if/when supported by Docker Ollama
- Model not found: The container now automatically pulls the configured model at startup. If issues persist, check logs for errors.

Roadmap
-------
- [x] Automate model download during startup (implemented via entrypoint script)
- [ ] Health check and readiness probe scripts
- [ ] Support additional LLM backends
- [ ] GPU support (as soon as available in Ollama Docker)
- [ ] Enhanced admin/monitoring tools

Entrypoint Script (/bin/init-entrypoint.sh)
-------------------------------------------
This script runs automatically when the Ollama container starts. It checks for the presence of the configured LLM model and pulls it if not already available. This ensures the model is ready before the service starts, enabling seamless and automated deployment without manual steps.

Contributing
------------
Pull Requests and Issues are welcome!
For questions or support, please open an issue on GitHub.

(c) 2025 AiDevOps Project / [Tokyoyabanjin]