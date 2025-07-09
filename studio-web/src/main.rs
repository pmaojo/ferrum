//! Binary entry point for running the web studio with `cargo leptos`.

use leptos::*;
use studio_web::app::App;

fn main() {
    mount_to_body(App);
}

