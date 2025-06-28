use async_trait::async_trait;
use uuid::Uuid;

use crate::shared_models::users::Users;

#[async_trait]
pub trait Userreaderport {
    async fn get_users(&self, id: Uuid) -> Users;
}
