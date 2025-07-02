# Leptos Frontend with Trunk

Ferrum can scaffold a Leptos frontend using the `--frontend leptos` flag. The generated crate lives under `frontend_leptos/` and is built with [Trunk](https://trunkrs.dev/).

## Development

Start the backend and Leptos frontend together:

```bash
ferrum dev
```

This runs `trunk serve` in the `frontend_leptos` directory.

## Production Build

The `ferrum build` command also builds the Leptos frontend with `trunk build --release`.
