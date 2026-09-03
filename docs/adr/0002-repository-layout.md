# ADR 0002: Repository layout for backend, frontend and deployment

Status: Accepted

Date: 2026-09-04

## Context

FoxForge started with the Python package and tests at repository root because the first implementation phases focused on printer-domain contracts, adapters, fleet services and queue safety.

The project now also has a runnable TypeScript web frontend and is explicitly targeting Docker/ARM64/Umbrel deployment. Keeping Python source at root while frontend and future deployment assets use dedicated top-level directories makes ownership and CI boundaries less obvious and will become increasingly awkward once the public API, inventory, compiled web assets and deployment packaging are added.

The desired long-term shape is:

```text
FoxForge/
├── backend/
│   ├── pyproject.toml
│   ├── src/foxforge/
│   └── tests/
├── frontend/
└── deployment/
    ├── docker/
    └── umbrel/
```

Repository-level documentation, licensing, GitHub metadata and shared project history remain at root.

## Decision

FoxForge will use three explicit top-level implementation areas:

- `backend/` for Python 3.12+ application/core code, tests and Python packaging metadata;
- `frontend/` for the TypeScript/React application and its build tooling;
- `deployment/` for packaging the same FoxForge runtime for Docker and Umbrel.

The Python package name remains `foxforge`; moving the source does not rename domain modules or adapter imports. Backend CI runs with `backend/` as its working directory so existing relative architecture tests continue to validate package boundaries.

The public REST/WebSocket API belongs to the backend application boundary. It must expose application services and typed capabilities rather than let the frontend or HTTP handlers bypass them to raw Bambu/Moonraker transports.

The frontend target stack is TypeScript + React + Vite + TanStack Query + React Router + i18next. The production frontend compiles to static assets and does not require a Node.js runtime in the production container.

Deployment packaging is downstream of backend/frontend artifacts. Docker and Umbrel must not fork core behavior; Umbrel packages the same tested FoxForge runtime used by generic self-hosted Docker deployments.

## Alternatives

### Keep Python at repository root

This minimizes path changes now, but the repository becomes asymmetrical as `frontend/` and `deployment/` grow. It also makes future backend-only CI, Docker build contexts and contributor navigation less clear.

Rejected as the long-term layout.

### Use a single monolithic `src/` tree for Python and TypeScript

This makes language/tool boundaries harder to reason about and couples unrelated build systems.

Rejected.

### Split backend and frontend into separate repositories

This provides maximum isolation but weakens atomic API contract changes, shared release/versioning, self-hosted packaging and project documentation. FoxForge is intended to ship as one integrated application.

Rejected for the current project stage.

### Put deployment files at repository root

A root `Dockerfile` can be convenient, but FoxForge expects both generic Docker and Umbrel packaging plus future deployment-specific validation. A dedicated area keeps packaging concerns explicit.

Rejected as the canonical layout. A future tiny root convenience file may delegate to `deployment/` if it materially improves developer ergonomics.

## Consequences

Positive:

- clearer ownership boundaries for Python, TypeScript and deployment code;
- CI can trigger and run per area;
- future API/frontend changes remain in one repository while still being structurally separated;
- Docker/ARM64/Umbrel packaging has an explicit home;
- easier contributor navigation as inventory, AMS/CFS and API modules grow.

Costs:

- existing Python development commands must run from `backend/` or specify its paths;
- documentation and workflow path references need migration;
- local clones must update after the move;
- open branches based on the old root layout may require rebasing.

The move is intentionally mechanical: it must not alter Python module names, queue semantics, adapter behavior or persistence behavior.

## Migration plan

1. Move `pyproject.toml`, `src/` and `tests/` into `backend/` without changing the Python package namespace.
2. Add `backend/README.md` with backend-specific development commands.
3. Update backend CI triggers and set `working-directory: backend`.
4. Update durable documentation to reference `backend/src/foxforge/...` where repository paths are named explicitly.
5. Keep the existing `frontend/` top-level directory and evolve it independently.
6. Add `deployment/docker/` and `deployment/umbrel/` ownership/readme skeletons before production packaging arrives.
7. When REST/WebSocket work begins, place it under the backend package and document its application-service boundary before wiring the frontend to it.

## Acceptance criteria

- `backend/pyproject.toml`, `backend/src/foxforge/` and `backend/tests/` contain the existing Python project with no package-namespace change;
- root `src/`, root `tests/` and root `pyproject.toml` are removed;
- existing Python tests, Ruff lint and Ruff format checks pass from `backend/` on Python 3.12 and 3.13;
- architecture tests still enforce domain/application independence from vendor adapters;
- `frontend/` remains independently buildable;
- `deployment/docker/` and `deployment/umbrel/` have documented ownership boundaries;
- README and docs describe the new layout;
- no runtime feature behavior changes are included in the layout migration.
