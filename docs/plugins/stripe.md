# Stripe Plugin

This plugin integrates [stripe-rust](https://crates.io/crates/stripe) to handle payments.
It ensures required keys in `.env` and scaffolds a webhook handler at `/api/stripe/webhook`.

## Usage

```bash
ferrum add stripe
ferrum compile gen/app.yaml
```

Add your credentials to `.env`:

```
STRIPE_SECRET=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

Run `ferrum dev` and expose the webhook endpoint to Stripe using a tool like `stripe listen`.
