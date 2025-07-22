# Plugin Development

Ferrum plugins extend the CLI and generator. Each plugin implements the `Plugin` trait provided by `ferrum-engine`:

```rust
pub trait Plugin: Send + Sync {
    fn name(&self) -> &'static str;
    fn on_init(&self) -> anyhow::Result<()> { /* optional */ }
    fn on_compile(&self) -> anyhow::Result<()> { /* optional */ }
    fn extend_dsl(&self, dsl: &mut ferrum_shared_models::FerrumDsl) -> anyhow::Result<()> { /* optional */ }
}
```

- **on_init**: executed right after `ferrum init` so a plugin can copy templates or set up files.
- **on_compile**: called once code generation finishes.
- **extend_dsl**: receives the parsed `FerrumDsl` AST before generation, allowing the plugin to inject nodes, jobs or resources.

## Building a Dynamic Plugin

Create a crate with `cdylib` type and expose a `plugin_create` function returning your plugin:

```rust
#[no_mangle]
pub extern "C" fn plugin_create() -> Box<dyn Plugin> {
    Box::new(MyPlugin)
}
```

Build the library in release mode:

```bash
cargo build --release
```

Then write a `plugin.toml` file pointing to the compiled artifact:

```toml
name = "my-plugin"
version = "0.1.0"
library = "target/release/libmy_plugin.so"
```

Register it with the CLI:

```bash
ferrum add path/to/my-plugin
```

Ferrum loads the `plugin.toml` during `ferrum compile`, opens the library and calls `plugin_create`. From that point your hooks run alongside the built-in ones.

Use [ferrum-plugin-template](../ferrum-plugin-template/README.md) as a minimal starting point and browse the existing [plugin docs](.) for concrete examples.
