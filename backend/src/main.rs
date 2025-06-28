use axum::{routing::get, Router};
use std::net::SocketAddr;
use std::sync::Arc;

// This will be populated by the generated code
pub mod handlers;
pub mod routes;
pub mod db;
pub mod usecases;

// Shared state for the application
pub struct AppState {
    // Repositories will be added here by the generated code
}

#[tokio::main]
async fn main() {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();

    // Create application state
    let app_state = Arc::new(AppState {});

    // Build the router
    let app = Router::new()
        .route("/", get(|| async { "Ferrum API Server" }))
        .with_state(app_state);

    // Add routes from generated modules
    // This will be populated by the generated code

    // Run the server
    let addr = SocketAddr::from(([0, 0, 0, 0], 3000));
    tracing::info!("Listening on {}", addr);
    
    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}
