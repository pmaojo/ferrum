use axum::{extract::State, Json};
use uuid::Uuid;

use crate::shared_models::user::User;
use crate::usecases::users::getUser;

pub async fn getUser_handler(
    State(state): State<crate::AppState>,
    
    Json(payload): Json<getUser::Request>,
    
) -> Json<User> {
    let result = getUser::execute(
        &state.userRepository,
        
        payload,
        
    ).await;

    Json(result)
}
