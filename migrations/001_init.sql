-- agent_platform schema: department entitlement model.
-- App-owned tables only — agno's own tables (sessions/memory/knowledge/vector)
-- live in the same schema but are created/managed by agno itself.
-- Every statement is idempotent so this applies cleanly to a blank or existing DB.

CREATE SCHEMA IF NOT EXISTS agent_platform;

CREATE TABLE IF NOT EXISTS agent_platform.users (
    serial_id       int4 NOT NULL GENERATED ALWAYS AS identity primary key,
    id              uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    email           text NOT NULL UNIQUE,
    display_name    text NOT NULL,
    department_key  text REFERENCES agent_platform.departments (key),
    active          boolean NOT NULL DEFAULT true,
    workos_user_id  text UNIQUE,
    last_login_at   timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now()
	created_by_id   uuid NOT null REFERENCES agent_platform.users(id),
	updated_at      timestamptz NULL,
	updated_by_id   uuid null REFERENCES agent_platform.users(id)
);

CREATE TABLE IF NOT EXISTS agent_platform.domains (

);

CREATE TABLE IF NOT EXISTS agent_platform.domain_users (

);



CREATE TABLE IF NOT EXISTS agent_platform.tools (

);

CREATE TABLE IF NOT EXISTS agent_platform.domain_tools (

);

