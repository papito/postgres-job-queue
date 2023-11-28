DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

CREATE TABLE job(
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type TEXT NOT NULL,
    arguments JSONB NOT NULL DEFAULT '{}'::JSONB,
    unique_signature VARCHAR GENERATED ALWAYS AS (md5(job_type || arguments::text)) STORED,
    tries INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL,
    base_retry_minutes INT NOT NULL,
    -- NULL ripe time means the job is immediate and runs as soon as a worker is ready to rumble
    ripe_at TIMESTAMPTZ DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT NULL
);

CREATE INDEX job_ripe_at_idx ON job(ripe_at);
CREATE UNIQUE INDEX job_unique_signature_idx ON job(unique_signature);

CREATE OR REPLACE FUNCTION update_changed_at()
    RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
RETURN NEW;
END;
$$ language 'plpgsql';


CREATE TRIGGER trigger_rec_updated_job
    BEFORE INSERT OR UPDATE ON job
    FOR EACH ROW EXECUTE PROCEDURE update_changed_at();
