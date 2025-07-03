# Leptos Frontend with Trunk

Ferrum can scaffold a Leptos frontend using the `--frontend leptos-csr` or `--frontend leptos-ssr` flag. The generated crate lives under `frontend_leptos/` and is built with [Trunk](https://trunkrs.dev/). CSR produces a client-side rendered app while SSR enables server-side rendering with Axum.

## Development

Start the backend and Leptos frontend together:

```bash
ferrum dev
```

This runs `trunk serve --features=csr` or `--features=ssr` in the `frontend_leptos` directory depending on the selected mode.

## Production Build

The `ferrum build` command also builds the Leptos frontend with `trunk build --release --features=csr` or `--features=ssr`.
