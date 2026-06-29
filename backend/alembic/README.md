# Database migrations (Alembic)

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/).
The ORM models live in `src/utils/models/` (all sharing one `Base`); Alembic
diffs the database against `Base.metadata`.

## How it works at runtime

`Database._init_schema()` (in `src/utils/database.py`) runs automatically the
first time `get_db()` is called:

- **Brand-new DB** → builds the current schema with `create_all()` and stamps it
  at the latest revision.
- **Pre-Alembic DB** (tables but no `alembic_version`) → stamped at the baseline,
  then upgraded.
- **Managed DB** → `upgrade head` applies any pending migrations.

So in normal use (dev or Docker) you don't run anything by hand — the app
migrates itself on startup. The DB URL always matches `get_db()` because
`alembic/env.py` resolves it from `src.utils.paths` (repo-root `data/`, or
`/app/data` in Docker).

## Changing the schema

1. Edit the model(s) under `src/utils/models/`.
2. Generate a migration (run from `backend/`):

   ```bash
   python -m alembic revision --autogenerate -m "describe the change"
   ```

3. **Review the generated file** in `alembic/versions/` — SQLite autogenerate
   can miss/emit spurious ops; migrations use batch mode for ALTERs.
4. Apply it (or just start the app, which runs `upgrade head`):

   ```bash
   python -m alembic upgrade head
   ```

## Useful commands

```bash
python -m alembic current              # show the DB's current revision
python -m alembic history              # list migrations
python -m alembic downgrade -1         # roll back one revision
```

To autogenerate against an empty database (e.g. to regenerate a full baseline),
set `ALEMBIC_DB_URL=sqlite:////tmp/scratch.db` for the command.
