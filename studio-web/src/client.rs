//! Binary entry point for running the web studio in the browser (CSR).

use leptos::*;
use studio_web::app::App;

fn main() {
    mount_to_body(App);
} 