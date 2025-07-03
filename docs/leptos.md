# Leptos Frontend with cargo-leptos

Ferrum can scaffold a Leptos frontend using the `--frontend leptos-csr` or `--frontend leptos-ssr` flag. The generated workspace lives under `frontend_leptos/` and is built with [cargo-leptos](https://github.com/leptos-rs/cargo-leptos). CSR produces a client-side rendered app while SSR enables server-side rendering with Axum.

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
