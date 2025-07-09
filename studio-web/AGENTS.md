# Guidelines for `studio-web`

This crate implements the browser-based version of Ferrum Studio. Keep the code
modular and easy to test. Follow these conventions:

- Adhere to SOLID principles and prefer composition over inheritance.
- Public APIs must be documented with Rustdoc comments.
- Always provide unit tests for new functionality under `tests/`.
- When adding HTTP calls or async logic, abstract them behind traits so they can
  be mocked.
- Run `cargo test -p studio-web` before every commit that touches this crate.

Development focuses on the Leptos frontend. The folder structure mirrors the
Bevy desktop studio but many modules are placeholders awaiting implementation.
Use TODO comments with short guidance when stubbing features.
