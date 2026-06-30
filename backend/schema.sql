CREATE TABLE IF NOT EXISTS scans (
    id TEXT PRIMARY KEY,
    subnet TEXT NOT NULL,
    interface TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    total_devices INTEGER NOT NULL DEFAULT 0,
    cameras_found INTEGER NOT NULL DEFAULT 0,
    high_risk_count INTEGER NOT NULL DEFAULT 0,
    scan_engine TEXT NOT NULL,
    scan_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scans_started_at ON scans(started_at DESC);
