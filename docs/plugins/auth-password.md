# Auth Password Plugin

This plugin adds basic password-based authentication scaffolding.
Refresh tokens are issued and persisted in Redis automatically.

## Usage

```bash
ferrum add auth-password
ferrum compile gen/app.yaml
```

The plugin copies login handlers, session helpers using Redis and frontend components to your project. It ensures the following variables in `.env`:

```
JWT_SECRET=change_me
AUTH_REDIRECT=/login
REDIS_URL=redis://localhost:6379
```
