# Auth OAuth Plugin

This plugin scaffolds Google and GitHub OAuth login flows.
 
It also generates helpers for refresh tokens stored in Redis and exposes a `/api/auth/refresh` endpoint.


## Usage

```bash
ferrum add auth-oauth
ferrum compile gen/app.yaml
```

After adding the plugin, configure the following keys in your `.env`:

```
JWT_SECRET=your-secret
REDIS_URL=redis://localhost:6379
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

Run `ferrum dev` and navigate to `/api/auth/google` or `/api/auth/github` to begin the OAuth flow.
