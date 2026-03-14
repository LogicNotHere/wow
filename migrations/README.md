# Alembic Integration Notes

This project uses one monolith app and one shared PostgreSQL database.

## Metadata source

Use one shared metadata for all modules:

```python
from wow_shop.infrastructure.db.models import metadata as target_metadata
```

`wow_shop.infrastructure.db.models` imports all module model files and
registers every table in `Base.metadata`.

## Expected model layout

- `wow_shop/modules/<module>/infrastructure/db/models.py` - module-owned ORM
- `wow_shop/infrastructure/db/base.py` - global `Base` + naming convention
- `wow_shop/infrastructure/db/session.py` - engine and async session factory
- `wow_shop/infrastructure/db/models.py` - import aggregator for Alembic

## Typical Alembic commands

```bash
alembic revision --autogenerate -m "init schema"
alembic upgrade head
```
