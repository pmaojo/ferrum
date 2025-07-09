# Studio Web

This crate provides a lightweight web version of Ferrum Studio implemented with [Leptos](https://github.com/leptos-rs/leptos).
It targets the same API endpoints used by the Bevy desktop client but runs entirely in the browser.

## Running

Build and serve using `cargo-leptos`:

```bash
cargo leptos serve --manifest-path studio-web/Cargo.toml
```

The server automatically recompiles on changes and opens a browser window with the app.
