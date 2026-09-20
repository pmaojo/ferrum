use axum::{routing::get, Router};
use std::net::SocketAddr;
use std::path::PathBuf;
use axum_server::tls_rustls::RustlsConfig;
use rustls_acme::{caches::DirCache, AcmeConfig};
use tokio_stream::StreamExt;
use tower_http::services::{ServeDir, ServeFile};

#[tokio::main]
async fn main() {
    // Load configuration from environment variables
    let port = std::env::var("PORT").unwrap_or_else(|_| "3000".to_string()).parse::<u16>().unwrap();
    let https = std::env::var("HTTPS").unwrap_or_else(|_| "false".to_string()) == "true";
    let domain = std::env::var("DOMAIN").ok();
    let email = std::env::var("EMAIL").ok();
    let static_dir = std::env::var("STATIC_DIR").ok();

    let mut app = Router::new().route("/api/health", get(|| async { "Ferrum API is healthy" }));

    // Serve static files (SPA support)
    if let Some(dir) = static_dir {
        let path = PathBuf::from(dir);
        if path.exists() {
            let serve_dir = ServeDir::new(&path)
                .not_found_service(ServeFile::new(path.join("index.html")));
            app = app.fallback_service(serve_dir);
            println!("📂 Serving static files from {:?}", path);
        } else {
            println!("⚠️  Static directory {:?} does not exist", path);
        }
    } else {
         app = app.route("/", get(|| async { "Hello Ferrum" }));
    }

    if https {
        if let Some(domain) = domain {
            println!("🔒 Starting HTTPS server on port 443 for domain {}", domain);

            let mut state = AcmeConfig::new(vec![domain.clone()])
                .contact(email.iter().map(|e| format!("mailto:{}", e)))
                .cache_option(Some(DirCache::new("certs")))
                .directory_lets_encrypt(true)
                .state();

            let acceptor = state.axum_acceptor(state.default_rustls_config());

            tokio::spawn(async move {
                let state = state.clone();
                loop {
                    match state.next().await.unwrap() {
                        Ok(ok) => println!("event: {:?}", ok),
                        Err(err) => println!("error: {:?}", err),
                    }
                }
            });

            let addr = SocketAddr::from(([0, 0, 0, 0], 443));
            let listener = axum_server::bind(addr).acceptor(acceptor);
            println!("🚀 HTTPS Server running on https://{}", domain);

            // Optional HTTP redirect
            tokio::spawn(async move {
                let redirect_app = Router::new().fallback(move |host: axum::extract::Host, uri: axum::http::Uri| async move {
                    let url = format!("https://{}{}", host, uri);
                    axum::response::Redirect::permanent(&url)
                });
                let addr = SocketAddr::from(([0, 0, 0, 0], 80));
                println!("↩️  Redirecting HTTP traffic from port 80 to HTTPS");
                axum_server::bind(addr)
                    .serve(redirect_app.into_make_service())
                    .await
                    .unwrap();
            });

            listener.serve(app.into_make_service()).await.unwrap();
        } else {
            eprintln!("❌ HTTPS enabled but DOMAIN env var is missing");
            std::process::exit(1);
        }
    } else {
        let addr = SocketAddr::from(([0, 0, 0, 0], port));
        println!("🚀 Backend running on {}", addr);
        axum_server::bind(addr)
            .serve(app.into_make_service())
            .await
            .unwrap();
    }
}
