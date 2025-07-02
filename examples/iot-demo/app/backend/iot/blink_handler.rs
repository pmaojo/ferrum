use axum::{Json, extract::State};
use std::sync::Arc;
use crate::AppState;

pub async fn blink_handler(State(_state): State<Arc<AppState>>) -> Json<()> {
    // Exposed via POST /iot/blink
    // ⛳ AI_FILL[iot_http] --context=iot:blink
    Json(())
}
