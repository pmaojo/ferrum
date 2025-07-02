use leptos::*;
use leptos_axum::{generate_route_list, LeptosRoutes};
use axum::Router;

mod app;
use app::App;

#[tokio::main]
async fn main() {
    let conf = get_configuration(None).await.unwrap();
    let leptos_options = conf.leptos_options;
    let addr = leptos_options.site_addr;
    let routes = generate_route_list(App);
    let app = Router::new().leptos_routes(&leptos_options, routes, App);
    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}
