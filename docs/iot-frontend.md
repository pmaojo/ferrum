# IoT Section

Ferrum lets you declare hardware drivers under the `iot:` section of
`grafo.yaml`. Each item provides Rust code that will be copied into
`backend/iot/` and can optionally be exposed to the frontend.

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
