# Architecture

## High-level components

- Noesis Noema (Client)
  - macOS/iOS native app
  - Collects user input and context
  - Displays evidence, routes, and final answers

- noema-agent (Server)
  - HTTP/gRPC API
  - Router
  - Policy Engine
  - Executors (LLMs / Tools / RAG backends)

## Data flow (happy path)

1. Client sends a structured request:
   - user query
   - intent metadata
   - environment (device/network)
   - privacy & cost policy

2. Router decides:
   - which backend to call
   - how much compute to spend
   - whether to enable agentic reasoning

3. Executor runs:
   - calls local/VPC/cloud LLMs
   - integrates RAG results
   - returns answer + evidence

4. Client renders:
   - answer
   - evidence
   - routing decision (for transparency)