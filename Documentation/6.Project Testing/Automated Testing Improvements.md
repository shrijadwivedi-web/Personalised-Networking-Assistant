# Automated Testing Improvements

Implemented production-readiness testing additions:

- JWT security tests for expired tokens, invalid signatures, missing subjects, and unknown users.
- Password-hashing verification that confirms plaintext passwords are not stored.
- Protected-endpoint authentication checks across all authenticated API routes.
- User-isolation tests for feedback and profile data.
- Validation-boundary tests for usernames, profile length, and invalid request types.
- Rate-limit tests for `/generate-conversation` and `/fact-check`.
- Database rollback tests for history, feedback, and profile persistence.
- Gemini prompt and empty-output parser tests.
- Wikipedia timeout, malformed JSON, and URL-format tests.
- Coverage configuration for `app` and `frontend`.
- GitHub Actions CI for pytest coverage, Bandit, pip-audit, and Docker image builds.
- Optional manual CI jobs for Playwright E2E and live AI evaluation.
- Locust performance scenario for narrow backend load testing.

Default CI intentionally excludes:

- `e2e`
- `performance`
- `live_ai`

Those suites require running services, browser dependencies, deliberate load-test settings, or live provider credentials.
