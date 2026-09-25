# Ferrum DSL Reference

Ferrum projects revolve around a single `grafo.yaml` file that defines modules, nodes and additional features. The DSL follows Hexagonal Architecture and aims to keep code generation SOLID and test-friendly.

## Basic Structure

A minimal module looks like this:

```yaml
module: users
nodes:
  - id: getUser
    type: usecase
    input:
      - name: userId
        type: uuid
    output: User
    depends_on: [userRepository]

  - id: userRepository
    type: adapter
    implements: userReaderPort

  - id: userReaderPort
    type: port
```

## Additional Sections

Ferrum extends the DSL with several high level declarations. The [README](../README.md) shows them in context and the [development plan](../PLAN.md) lists when they were introduced. Supported sections include:

- **queries** → generates Rust handlers and React hooks
- **mutations** → like queries but for changing state; can require auth
- **routes / pages** → creates a `frontend/src/routes.tsx` router plus placeholder pages in `frontend/src/pages/`
- **jobs** → scheduled tasks placed in `backend/jobs/`
- **resources** → integrations with external services (APIs, queues...)
- **policies** → reusable authorization guards
- **auth** → authentication setup (`userEntity` and `methods`)
- **forms** → declarative forms shared with the frontend
- **validations** → shared validation rules
- **iot** → drivers and React hooks via the `expose` mechanism

These capabilities are summarised in `PLAN.md`:

```text
- `auth` `{ userEntity, methods }`
- `route` `{ path, screen, authRequired }`
- `job`, `mutation`, `query`
- `policy` or `guard`
- `resource` for external integrations
```

## Example with Extended Features

The README provides a more complete example including forms, validations, resources and policies:

```yaml
forms:
  - name: LoginForm
    submitTo: loginUser
    fields:
      email: string
      password: string

validations:
  - name: emailIsValid
    appliesTo: users.registerUser.email
    rule: "email must match regex /@/"

resources:
  - name: cache
    type: redis

policies:
  - name: isAdmin
    guard: check_admin

iot:
  - name: blinkLed
    code: |
      use rppal::gpio::Gpio;
      pub fn blink_led() {
          let pin = Gpio::new().unwrap().get(17).unwrap().into_output();
          pin.set_high();
      }
```

### Jobs

Plugins or features can inject jobs automatically. As shown in the README:

```yaml
jobs:
  - name: example_job
    schedule: "0 0 * * *"
    handler: example_job
```

Use plugins like `cron` to add these sections without manual repetition.

---

Consult the main [README](../README.md#-dsl-specification-grafoyaml) for more examples and tips.
