//! Servidor SSR para studio-web usando Leptos y Axum

use axum::{extract::{Path, RawQuery}, http::HeaderMap, response::IntoResponse, routing::get, Router};
use leptos::*;
use leptos_axum::{generate_route_list, LeptosRoutes};
use studio_web::app::App;
use std::net::SocketAddr;

async fn server_fn_handler(
    path: Path<String>,
    headers: HeaderMap,
    raw_query: RawQuery,
    req: axum::http::Request<axum::body::Body>,
) -> impl IntoResponse {
    leptos_axum::handle_server_fns_with_context(path, headers, raw_query, || (), req).await
}

#[tokio::main]
async fn main() {
    // Configuración de Leptos
    let conf = get_configuration(None).await.unwrap();
    let leptos_options = conf.leptos_options;
    let addr = SocketAddr::from(([0, 0, 0, 0], 3000));

    // Rutas SSR
    let routes = generate_route_list(App);
    let app = Router::new()
        .route("/api/*fn_name", get(server_fn_handler))
        .leptos_routes(&leptos_options, routes, App)
        .with_state(leptos_options.clone());

    println!("🚀 Servidor SSR escuchando en http://{}", addr);
    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}

