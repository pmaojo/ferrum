# Auth OAuth Plugin

This plugin scaffolds Google and GitHub OAuth login flows.

## Usage

```bash
ferrum add auth-oauth
ferrum compile gen/app.yaml
```

After adding the plugin, configure the following keys in your `.env`:

```
JWT_SECRET=your-secret
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

Run `ferrum dev` and navigate to `/api/auth/google` or `/api/auth/github` to begin the OAuth flow.
