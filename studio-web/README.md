# 🌐 Ferrum Studio Web

A lightweight web interface for exploring your architecture graphs. It shares the
same API as the Bevy desktop client but runs entirely in the browser using
[Leptos](https://github.com/leptos-rs/leptos).

This is now the default way to visualize Ferrum projects. The desktop variant
remains for power users and offline work.

## Running

Install `cargo-leptos` and launch the development server:

```bash
cargo install cargo-leptos
cargo leptos serve --manifest-path studio-web/Cargo.toml
```

The server rebuilds on changes and opens the application in your browser. Set
`FERRUM_API_BASE_URL` to point at your backend if it's not running on
`localhost:8001`.

## Project structure

The crate mirrors the modules of `studio-desktop`:

- `api` – abstractions for backend communication.
- `app` – Leptos components and application wiring.
- `graph`, `viewer`, `runtime`, `app_state`, `settings` – placeholders for future
  features matching the desktop flow.

Contributions should keep modules small and testable. See `AGENTS.md` for
coding guidelines.
