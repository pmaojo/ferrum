use axum::{routing::post, Router};

use crate::handlers::users::getUser_handler;

pub fn users_routes() -> Router {
    Router::new()
        .route("/users/getuser", post(getUser_handler))
}
