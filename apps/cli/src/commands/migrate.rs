use anyhow::Result;

#[cfg(feature = "postgres")]
pub fn migrate() -> Result<()> {
    use diesel::prelude::*;
    use diesel_migrations::{FileBasedMigrations, MigrationHarness};

    dotenvy::dotenv().ok();
    let database_url = std::env::var("DATABASE_URL")?;
    let mut conn = PgConnection::establish(&database_url)?;
    let migrations = FileBasedMigrations::find_migrations_directory()?;
    conn.run_pending_migrations(migrations)
        .map_err(|e| anyhow::anyhow!(e))?;

    println!("✅ Database migrations applied");
    Ok(())
}

#[cfg(not(feature = "postgres"))]
pub fn migrate() -> Result<()> {
    anyhow::bail!("database migrations require the ferrum-cli `postgres` feature")
}

