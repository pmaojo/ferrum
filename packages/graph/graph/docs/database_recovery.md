# Database Recovery Guide

This guide outlines how to back up, restore, and recover the Graph service database.

## Backup

Use the provided script to create a compressed backup of the PostgreSQL database:

```bash
./services/graph/database/backup.sh /path/to/backup.dump
```

Set `DB_HOST`, `DB_PORT`, `DB_NAME`, or `DB_USER` environment variables to override defaults.

## Restore

To restore from a backup file:

```bash
./services/graph/database/restore.sh /path/to/backup.dump
```

The script drops existing objects before loading the backup.

## Disaster Recovery

1. Stop the application containers.
2. Restore the latest backup using `restore.sh`.
3. Run database migrations to ensure the schema is up to date:
   ```bash
   alembic upgrade head
   ```
4. Restart the application stack.

Regular backups and verified restores are essential to ensure data resilience.
