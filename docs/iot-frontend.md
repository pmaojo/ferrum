# Propuesta de Soporte IoT en Frontend

Se propone extender la seccion `iot:` del `grafo.yaml` con un campo opcional `expose` que genere endpoints en el backend y hooks o componentes para el frontend.

```yaml
iot:
  - name: blinkLed
    code: |
      pub fn blink_led() { /* ... */ }
    expose: true
    endpoint: /iot/blink
```

Al compilar con `expose: true`, Ferrus crearia:

- Un handler en Axum que mapea `POST /iot/blink` a `blink_led()`.
- Un hook de React `useBlinkLed` y un componente opcional reutilizable.

Ejemplo de uso en React:

```tsx
const { mutate, isLoading } = useBlinkLed();
return <Button onClick={() => mutate()}>Parpadear LED</Button>;
```

Como extension opcional, `expose` puede ser un objeto mas detallado:

```yaml
iot:
  - name: blinkLed
    code: |
      pub fn blink_led() { /* ... */ }
    expose:
      method: POST
      path: /iot/blink
      generateHook: true
      generateComponent: true
```

Esto permitiria declarar el metodo y la ruta, ademas de elegir si se generan hook o componente.
