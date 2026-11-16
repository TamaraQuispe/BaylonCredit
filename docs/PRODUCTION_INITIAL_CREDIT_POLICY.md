# Production: first-credit review policy

Production enables `REQUIRE_PAID_CREDIT_HISTORY=true`. The public demo now also explicitly enables it in `docker-compose.demo.yml`. No schema migration or training is required.

When a client has no fully repaid credit, every evaluation is persisted with `payment_history_review` in factors, `approved=false`, zero automatic limit and zero confidence. The response exposes `requires_manual_review=true`. Buying for cash, aging the account or repeating evaluations does not unlock approval. A fully repaid credit permits normal risk/policy evaluation; it does not guarantee approval or prove future repayment.

Only an authenticated administrator can override the first-credit review. The request must explicitly contain `manual_override=true`, a reason of at least ten trimmed characters, and an amount no larger than the existing business maximum. The resulting `credit_overridden` audit contains actor, reason, amount, evaluation ID and credit ID. Credit sales cannot bypass review. Existing loans, payment records and past evaluations are not rewritten.

The screen hides misleading score/probability/automatic-limit assurances for this state, asks for owner review and requires checkbox/reason before requesting an exception. This does not impose an arbitrary starter amount: the administrator selects it conservatively within the configured maximum. The administrator role is the current technical representation of authorized ownership; operators cannot approve a first-credit exception.

## Current release

Small layer based on the previously deployed API, no dependency upgrades:

- `deploy/Dockerfile.history-policy`
- `docker-compose.history-policy.yml`, applied AFTER base and prod files, never demo
- Server release directory `/home/ubuntu/credify-history-policy`
- Images `credify-api-history-policy:v1` and `credify-frontend-history-policy:v1`
- Preserved rollback images `bayloncredit-api:history-policy-base` and `bayloncredit-frontend:before-history-policy`

Deployment command on the server:

```bash
docker compose --project-directory /home/ubuntu/BaylonCredit --env-file /home/ubuntu/BaylonCredit/.env.prod -f /home/ubuntu/BaylonCredit/docker-compose.yml -f /home/ubuntu/BaylonCredit/docker-compose.prod.yml -f /home/ubuntu/credify-history-policy/docker-compose.history-policy.yml up -d --no-deps --no-build api frontend
```

Frontend release was built from tracked production baseline plus the evaluation/form/repository/date/layout files required by this policy, not all uncommitted demo UI files. Production source copies and latest-image aliases were updated to preserve the change on a regular rebuild; the release has not been committed to Git. Do not run an unattended Git pull over the modified server source. Review and commit only when requested.

Verification: 78 backend tests, including 20 focused cases; local browser verification for admin/operator desktop/mobile with mocked API; public bundle and health checks; runtime read-only policy check. All current active production clients had repaid credit, so the no-history runtime check used a controlled in-memory feature vector and real read-only DB queries, not a newly created production client. No test client, loan or evaluation was persisted. Counts remained four credits and seventeen evaluations at verification.

The VM has limited memory. A temporary second API caused transient healthcheck timeouts and was stopped; primary API and demo recovered. Numerical-thread limits are included in this release. Compile frontend off-server and do not train a model concurrently with serving production.

No real-trained model, external credit-bureau history, consent workflow or starter-amount recommendation was introduced by this release.
