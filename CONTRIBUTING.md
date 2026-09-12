# Contributing

Thanks for helping keep this workshop agent safe and easy to run.

## Before you open a PR

1. Never commit `.env`, tokens, API keys, or real `AGENT_SEED` values.
2. Run tests:

```bash
python -m unittest discover -s tests -v
```

3. Keep person mentions opt-in. Do not hardcode tagging a real person by default.
4. Prefer small, focused changes with a short explanation of why.

## Local security checklist

- Use a unique `AGENT_SEED`.
- Do not print access tokens in scripts or docs.
- Chat error messages must not leak secrets.
- Scheduled drafts should go only to the claimed owner.
