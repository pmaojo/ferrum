# Leptos Frontend with cargo-leptos

Ferrum can scaffold a Leptos workspace using the `--frontend leptos-csr` or
`--frontend leptos-ssr` flag during `ferrum init`. The code is placed in
`frontend_leptos/` and is built with
[cargo-leptos](https://github.com/leptos-rs/cargo-leptos).

## Client-side rendering (CSR)

CSR ships the UI as WebAssembly that hydrates in the browser. Create a project
with:

```bash
ferrum init my-app --frontend leptos-csr
```

`ferrum dev` will run `cargo leptos watch --open` so the browser reloads when
you edit files.

## Server-side rendering (SSR)

SSR renders the app on the server using `leptos_axum`. Initialize it with:

```bash
ferrum init my-app --frontend leptos-ssr
```

To enable SSR in an existing Axum backend add `leptos_axum` and mount the
routes:

```rust
use axum::Router;
use leptos_axum::{generate_route_list, LeptosRoutes};

let routes = generate_route_list(App);
let app = Router::new()
    .leptos_routes(&options, routes, || view! { <App/> })
    .fallback(leptos_axum::file_and_error_handler(shell));
```

## Development

Start the backend and Leptos frontend together:

```bash
ferrum dev
```

This runs `cargo leptos watch --open` in the `frontend_leptos` directory.

## Production Build

The `ferrum build` command also builds the Leptos frontend with `cargo leptos build --release`.

Install the tool with:

```bash
cargo install cargo-leptos
```

