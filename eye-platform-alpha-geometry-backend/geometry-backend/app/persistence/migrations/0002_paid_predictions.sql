CREATE TABLE paid_predictions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    job_id TEXT,
    status TEXT NOT NULL,
    prediction_id TEXT,
    model_reference TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX paid_predictions_status_idx ON paid_predictions(status);
