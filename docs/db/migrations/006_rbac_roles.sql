-- 006_rbac_roles.sql — three-persona RBAC
-- Remaps the legacy role vocabulary (viewer|analyst|admin) to the persona model
-- the dashboard is restructured around: engineer | data_scientist | admin.
--   engineer       — Telecom Engineer: OSS/BSS ops, results, automation (default)
--   data_scientist — model internals, training, evaluation, data drift, notebooks
--   admin          — user/role management, L4 envelope, settings, pipeline/data
--
-- Idempotent: safe to re-run. Applied by data-init on fresh DBs (schema.sql mirrors
-- the default) and manually on existing DBs via:
--   docker compose exec -T postgres psql -U telecom -d telecom_intel -f - < docs/db/migrations/006_rbac_roles.sql

-- 1. Remap legacy values to the persona vocabulary (must run before any CHECK).
UPDATE users SET role = 'engineer'       WHERE role IN ('viewer', '') OR role IS NULL;
UPDATE users SET role = 'data_scientist' WHERE role = 'analyst';
-- 'admin' is unchanged.

-- 2. New default = engineer (signups + OAuth upserts land here; admin promotes).
ALTER TABLE users ALTER COLUMN role SET DEFAULT 'engineer';

-- 3. Seed admin: promote the project owner's account (if present).
UPDATE users SET role = 'admin' WHERE email = 'souhaylguenichi@gmail.com';

-- 4. Constrain to the three personas. Drop first so re-runs don't error.
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users
  ADD CONSTRAINT users_role_check
  CHECK (role IN ('engineer', 'data_scientist', 'admin'));
