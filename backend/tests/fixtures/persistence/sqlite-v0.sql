PRAGMA user_version = 0;

CREATE TABLE queue_entries (
    queue_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

INSERT INTO queue_entries(queue_id, payload, created_at, updated_at)
VALUES ('legacy-queue', '{"schema_version":1}', '2026-09-01T00:00:00+00:00', '2026-09-01T00:00:00+00:00');
