use async_trait::async_trait;
use sqlx::PgPool;

use crate::ports::userReaderPort;
use crate::shared_models::users::Users;

pub struct Userrepository {
    pool: PgPool,
}

impl Userrepository {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl Userreaderport for Userrepository {
    async fn get_users(&self, id: uuid::Uuid) -> Users {
        // In a real implementation, this would query the database
        // For now, we return a placeholder
        Users {
            id,
            name: "Example".to_string(),
            created_at: chrono::Utc::now(),
        }
    }
}
