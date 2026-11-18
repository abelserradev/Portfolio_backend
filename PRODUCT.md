# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- Portfolio site (Next frontend) as primary client.
- Site owner/admin flows that seed or manage projects and chat sessions.
- Anonymous visitors only through consented analytics events and public project reads.

## Product Purpose

FastAPI backend for the Buildforge portfolio: project catalog, contact/chat sessions (estimate scoping), analytics event intake, and related APIs consumed by `Portfolio_frontend`. Success = reliable project data and safe intake of inquiries/analytics.

## Positioning

API for a studio portfolio and lead/chat intake — not a CMS for arbitrary sites.

## Operating Context

Python FastAPI + SQLAlchemy/asyncpg (Postgres), Redis optional, Docker/Coolify deploy, GitHub Actions CI. Seeds example projects on init when catalog empty.

## Capabilities and Constraints

- Models/services for projects, project status, chat sessions, analytics.
- Rate limiting (slowapi); env-based settings.
- No first-party UI in this repo.
- Agent DB guardrails: read-only against shared/prod unless explicitly authorized.

## Brand Commitments

- Serves **Buildforge** portfolio content; project seed copy is Spanish/technical portfolio material.

## Evidence on Hand

- `app/` (models, services, init_db seeding), `requirements.txt`, Coolify workflow docs.
- Do not invent billing, multi-tenant SaaS claims, or client NDAs.

## Product Principles

1. Catalog and chat data are the source of truth for the public site.
2. Analytics events are optional and must respect frontend consent.
3. Seed data is demo/bootstrap only — never present as fabricated client wins in product copy without real content.
4. Keep security defaults (validation, rate limits) ahead of convenience shortcuts.
