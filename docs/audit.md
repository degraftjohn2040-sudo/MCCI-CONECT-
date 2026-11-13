# Engineering audit

This is a review of the repository and its locally exercised behavior, not an independent penetration test, compliance assessment, or production certification. No real member data or external service credentials were used. At the initial commit, the repository contained only a README and no application, integration, database, or deployment configuration.

## Verified improvements

- **Authentication:** sessions are random and stored as hashes, expire, and use HTTP-only and SameSite cookies (Secure by default). A concurrent local password reset or deactivation is rechecked before a new session is issued. CLI reset/deactivation revokes existing sessions. Tests exercise these cases.
- **API and input handling:** authenticated mutations require CSRF tokens, admin/reader permissions are enforced server-side, API bodies are bounded to 64 KiB, validation errors do not echo input values, and SQL parameters are bound. Tests cover role denial, CSRF, validation redaction, and request limits.
- **Rate limiting:** sign-in attempts use a SQLite-backed, direct-peer fixed window shared by processes using the same database. A concurrent test verifies the limit. This is not a distributed edge defense and a proxy may make many users share a peer address.
- **Database and recovery:** additive migrations retain legacy member records, member edits use version checks to prevent silent overwrites, imports are atomic, and backup/restore commands refuse to overwrite an existing file. A restore copy revokes sessions. Tests use temporary SQLite files, not a production restore.
- **Dependencies and build:** Python 3.11 locks include hashes; a source distribution and wheel can be built and checked for application assets. Dependency advisory scans were run locally; results depend on the advisory database and are not proof of security.

## Query and performance observations

A local synthetic SQLite experiment with 10,000 member rows showed `EXPLAIN QUERY PLAN` using `members_name` for a name-prefix search, `members_email` and `members_phone` for the duplicate-contact OR query, and `attendance_date` for ordered attendance. On that one local run, 100 repeated executions took approximately 2.62 ms, 0.26 ms, and 0.11 ms respectively. These are query-only measurements, not endpoint benchmarks or production capacity estimates. Offset pagination can become expensive and move as data changes; SQLite serializes writers. No load, mobile-device, network-degradation, or accessibility benchmark has been completed.

## Remaining high-priority risks

1. No approved privacy/retention policy, church-specific role scopes, multi-tenant isolation, or comprehensive member-consent model. Avoid real personal data.
2. No MFA, self-service recovery, independent security review, tamper-proof audit trail, or complete account administration UI. In-flight requests already authorized may finish after deactivation.
3. TLS, shared edge throttling, request timeouts, encrypted storage and backups, offsite backup scheduling, monitoring, and incident response must be supplied and verified before deployment.
4. Forms, prayer, pastoral care, messaging, AI and Google integrations are not implemented. They require dedicated threat and privacy reviews before enabling them.
5. Browser end-to-end, assistive technology, load, production-network and real disaster-recovery drills remain outstanding. Hosted CI and secret-scanning results must be checked on GitHub; local checks alone do not establish them.
