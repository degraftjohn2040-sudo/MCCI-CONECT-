# Product requirements

## Goal

Help MCCI UCC Campus care for its community with an accessible, mobile-first, privacy-respecting workspace. The initial user is an authorized staff member, not an anonymous public user.

## Initial acceptance criteria

- A locally provisioned account can sign in and sign out; unauthenticated API requests cannot read records.
- Owner, admin and super_admin can create and read members, aggregate attendance and internal announcements. Pastor can read those records but cannot create them. Other recognized roles can read internal announcements only. All rules are enforced on the server.
- Authorized users can page through records. Empty, loading and error states are shown. Administrative changes create basic audit events.
- No live provider is connected by default, no example personal data is supplied, and sensitive data must not enter the repository.

## Next requirements to agree

Confirm the church's role hierarchy, zone/cell boundaries, consent and lawful basis, retention, member correction/deletion, pastoral confidentiality, public forms threat model, messaging opt-in, Workspace authorization, AI data handling, multilingual support, platform ownership, and accessibility targets before implementing those workflows. All requested role names are recognized, but their church-specific scopes are not yet modeled.
