# IoT Section

Ferrum lets you declare hardware drivers under the `iot:` section of
`grafo.yaml`. Each item provides Rust code that will be copied into
`backend/iot/` and can optionally be exposed to the frontend. Entries
also support optional `protocol`, `driver` and `simulate` fields to
control how the hardware is accessed.

Setting `simulate: true` will also generate a simple module under
`backend/iot/sim` that logs calls to stdout so you can test drivers
without physical hardware.

## Basic declaration

```yaml
iot:
  - name: blinkLed
    code: |
      pub fn blink_led() { /* ... */ }
    expose: true
```

With `expose: true` Ferrum generates:

- An Axum handler mapped to `POST /iot/blinkLed`.
- A React hook `useBlinkLed` and a reusable component `<BlinkLed />`.

```tsx
const { mutate, isLoading } = useBlinkLed();
return <Button onClick={() => mutate()} disabled={isLoading}>Blink</Button>;
```

## Detailed `expose` object

Instead of a boolean, you can pass an object with these fields:

| Field               | Type   | Description |
| ------------------- | ------ | ------------------------------------------------------------- |
| `method`            | string | HTTP method to expose (`GET`, `POST`, ...). |
| `path`              | string | Custom endpoint path. Defaults to `/iot/<name>`. |
| `protocol`          | string | `http` (default) or `ws` for a WebSocket endpoint. |
| `generateHook`      | bool   | Create a React hook `use<Name>`. |
| `generateComponent` | bool   | Scaffold a React component `<Name />`. |

Example:

```yaml
iot:
  - name: readTemperature
    code: |
      pub fn read_temperature() -> f32 { /* ... */ }
    expose:
      method: GET
      path: /sensors/temp
      protocol: http
      generateHook: true
      generateComponent: false
```

When compiled this exposes `GET /sensors/temp` and generates a `useReadTemperature` hook for your React app.

## Enabling hardware crates

The backend `Cargo.toml` declares optional features for common IoT
libraries. To try the examples under `templates/backend/iot`, compile
with:

```bash
cargo build -p backend --features hal,rppal,mqtt,ethercat
```

This pulls in `embedded-hal`, `rppal`, `rumqttc` and `ethercat-rs` so
you can use the provided module templates.

MQTT helpers are optional as well. Activate them in your `grafo.yaml`:

```yaml
app:
  name: demo
  features: [mqtt]
```

## Protocol, driver and simulate

These optional fields let you pick the underlying interface and whether to
generate a logging stub for tests.

| Field      | Type   | Description                                                                 |
| ---------- | ------ | --------------------------------------------------------------------------- |
| `protocol` | string | Interface to use (`gpio`, `mqtt`, `ethercat`, ...).                          |
| `driver`   | string | Name of the Rust crate or module that implements the protocol.              |
| `simulate` | bool   | Generate an extra module under `backend/iot/sim` that logs each invocation. |

Example declaration:

```yaml
iot:
  - name: blink_led
    protocol: gpio
    driver: rppal
    simulate: true
    code: |
      pub fn blink_led() {
          // ... real GPIO calls
      }

  - name: publish_data
    protocol: mqtt
    driver: rumqttc
    simulate: false
    code: |
      pub fn publish_data(topic: &str, payload: &[u8]) {
          // ... publish over MQTT
      }

  - name: move_motor
    protocol: ethercat
    driver: ethercat_rs
    simulate: true
    code: |
      pub fn move_motor(position: i32) {
          // ... drive motor via EtherCAT
      }
```

## CoAP backend service

Ferrum provides a lightweight CoAP client behind the optional `coap`
feature. The `engine::services::coap` module exposes async `get` and
`post` functions built on the [`coap`](https://crates.io/crates/coap)
crate. Enable the helpers in your `grafo.yaml`:

```yaml
app:
  name: demo
  features: [coap]
```

You can then call the service from a driver or usecase:

```rust
use ferrum_engine::coap;

async fn ping_sensor() -> anyhow::Result<Vec<u8>> {
    coap::get("coap://[fe80::1]/ping").await
}
```
