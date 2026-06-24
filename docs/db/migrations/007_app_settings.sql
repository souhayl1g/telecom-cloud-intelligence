-- 007_app_settings.sql — admin-managed dashboard settings (key/value)
-- Backs the Admin console "Settings" tab. JSONB values so a setting can be a
-- scalar, list, or object. Idempotent; mirrored default seed in schema.sql.

CREATE TABLE IF NOT EXISTS app_settings (
  key        TEXT PRIMARY KEY,
  value      JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by TEXT
);

-- Seed sensible defaults (no-op if already present).
INSERT INTO app_settings (key, value) VALUES
  ('refresh_interval_ms', '30000'::jsonb),
  ('default_theme',       '"dark"'::jsonb),
  ('demo_mode',           'false'::jsonb)
ON CONFLICT (key) DO NOTHING;
