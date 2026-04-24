# ForgeLink Runbooks

Operational playbooks. Each runbook answers one question: **"The thing broke / needs to rotate — what do I type?"**

## When to use a runbook vs. reading the code

- **Use the runbook** when you're on-call at 2am and need the steps that work.
- **Read the code** when you're doing a deliberate change and want to understand the mechanism.

## What every runbook promises

Every page in this directory follows the same shape:

1. **When to reach for this** — one sentence. If the situation doesn't match, close the page.
2. **Before you start** — what you need open, what access, what you'll affect.
3. **Steps** — numbered, runnable commands. Copy-paste should Just Work.
4. **Verify** — how you know the step worked.
5. **Rollback** — the commands that undo the change.
6. **Known pitfalls** — things we've already burned hours on.

## Index

| Runbook | When |
|---|---|
| [restart-all](restart-all.md) | Full stack is unhealthy; need a clean restart |
| [rotate-jwt-keys](rotate-jwt-keys.md) | IDP signing key rotation (scheduled or compromised) |
| [rotate-smtp-creds](rotate-smtp-creds.md) | SMTP password change (e.g. Postmark token rotation) |
| [recover-from-lost-cluster](recover-from-lost-cluster.md) | The K8s cluster is gone; rebuild from Git + backups |
| [full-stack-reinstall](full-stack-reinstall.md) | Clean-slate rebuild from zero (lab / new customer site) |

## Writing a new runbook

- Test every command against a running stack before you merge.
- Include the **expected output** after every command whose success you care about.
- Never write "just run `make foo`"; write out what `make foo` does so a first-time reader knows the side effects.
- Absolute paths. `cd` commands are fine; assuming you're in a specific directory is not.
