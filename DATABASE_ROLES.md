# Database roles and schema

The app uses role separation and a dedicated schema:

- **Schema**: All application tables live in the `app` schema. The `public` schema is unused.
- **app_migrator**: Owns the `app` schema and tables; allowed to perform DDL (CREATE/ALTER/DROP).
- **app_runtime**: Restricted to DML only (SELECT, INSERT, UPDATE, DELETE). Cannot drop or create tables.

## Application configuration

- **DATABASE_URL**: Must use the **app_runtime** role for the running API (FastAPI, Lambda, etc.). This prevents the app from dropping or altering tables.
- **DATABASE_MIGRATOR_URL** (optional): Use for one-off DDL scripts (e.g. creating indexes). When set, scripts like `create_indexes.py` and `create_table_matching_indexes.py` use this URL so they run as **app_migrator**.

## App-side behavior

- **database.py**: ORM models use `metadata = MetaData(schema="app")`, so all queries target the `app` schema.
- **DDL scripts** (`create_indexes.py`, `create_table_matching_indexes.py`): Use schema-qualified names (`app.<table>`) and prefer `DATABASE_MIGRATOR_URL` when set.
- **generate_erp_comment_updates.py**: `--schema` defaults to `app`.

## Checklist

1. Set `DATABASE_URL` to a connection string for **app_runtime** (e.g. `postgresql://app_runtime:...@host:5432/dbname`).
2. For running index/migration scripts, either set `DATABASE_MIGRATOR_URL` to **app_migrator** or run those scripts with migrator credentials in `DATABASE_URL` temporarily.
3. Ensure DB has `search_path` and default privileges set so `app_runtime` can use the `app` schema without elevated privileges.
