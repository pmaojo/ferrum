# Ferrus Plugin Template

This directory provides a minimal starting point for creating Ferrum plugins.

## Steps

1. Implement your plugin logic in `src/lib.rs` and expose a `plugin_create` function.
2. Build the plugin:
   ```bash
   cargo build --release
   ```
3. Ensure `plugin.toml` points to the compiled library under `target/release`.
4. Add the plugin to your project with `ferrum add path/to/ferrus-plugin-template`.
