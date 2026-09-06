# ADR 0002: Repository layout for backend, frontend and deployment

- **Status:** Accepted and implemented
- **Date:** 2026-09-04
- **Implementation update:** 2026-09-06

## Context

FoxForge is one integrated application with distinct Python, TypeScript and deployment toolchains. Keeping those ownership boundaries explicit improves CI, contributor navigation and release packaging without splitting API/frontend changes across repositories.

## Decision

The canonical top-level implementation areas are:

```text
FoxForge/
├── backend/       Python package, tests, API/runtime
├── frontend/      React/TypeScript/Vite application
├── deployment/    Docker/Umbrel packaging and contracts
├── docs/          Architecture/design/testing/status
├── integrations/  Isolated migration/provenance material
└── release/       Release identity and immutable notes
```

Repository-level licensing, GitHub metadata, changelog and project README remain at root.

The Python package remains named `foxforge`.

## Boundaries

- `backend/` owns domain/application code, adapters, persistence and the HTTP/SSE runtime;
- `frontend/` owns presentation and typed API clients; it does not define backend persistence/domain truth;
- `deployment/` packages the same tested FoxForge runtime for Docker and Umbrel; it must not fork product behavior;
- production frontend compiles to static assets served by the Python runtime, so no production Node.js process is required.

## Implementation state

The migration is complete:

- Python code/tests/package metadata live under `backend/`;
- React/Vite lives under `frontend/`;
- Docker/Umbrel ownership lives under `deployment/`;
- unified runtime serves the compiled SPA plus `/api/v1` and SSE;
- CI/release workflows operate on these explicit boundaries.

## Alternatives rejected

- keeping Python at repository root;
- mixing Python/TypeScript under one monolithic source tree;
- splitting backend/frontend into separate repositories;
- treating root-level deployment files as the canonical ownership model.

## Consequences

- clearer language/tool/deployment ownership;
- atomic API/frontend changes remain possible in one repository;
- Docker/ARM64/Umbrel packaging has an explicit home;
- development commands must use the appropriate subdirectory/toolchain.

## Acceptance criteria

- `backend/`, `frontend/` and `deployment/` remain independently understandable/buildable;
- backend architecture guards continue to apply after path/layout changes;
- deployment packaging consumes the same application behavior;
- documentation paths match the current tree;
- layout changes do not alter printer/queue/inventory semantics by themselves.
