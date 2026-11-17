# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Kill Bill is an open-source subscription billing and payments platform (Java, Maven multi-module, Apache 2.0). Docs: docs.killbill.io; REST API: apidocs.killbill.io. This repo is the core server; payment gateways, tax engines, etc. are external plugins. Contributing: discuss on the mailing list before opening issues/PRs (see `.github/CONTRIBUTING.md`); new code should come with tests.

## Build, test, run

Parent POM is `org.kill-bill.billing:killbill-oss-parent` (build config, plugin versions, and the `check.*` quality gates come from there). Dependencies such as `killbill-api`, `killbill-commons`, `killbill-platform` are separate repos resolved from Maven repositories.

- Build everything: `mvn clean install -DskipTests`
- Skip quality gates for fast iteration (same flags `bin/start-server` uses): `-Dcheck.skip-dependency=true -Dcheck.skip-dependency-scope=true -Dcheck.skip-dependency-versions=true -Dcheck.skip-duplicate-finder=true -Dcheck.skip-enforcer=true -Dcheck.skip-rat=true -Dcheck.skip-spotbugs=true`
- One module (and what it depends on): `mvn -pl invoice -am install -DskipTests`
- Single test class / method (TestNG + Surefire): `mvn -pl invoice test -Dtest=TestFoo` or `-Dtest=TestFoo#testBar`
- Run the server (Jetty, port 8080, uses `profiles/killbill`): `bin/start-server -s` (`-d` debug on 12345, `-p` port). Config defaults in `profiles/killbill/src/main/resources/killbill-server.properties`.
- Many tests need a database (embedded H2 or MySQL/Postgres via the shared test harness in `killbill-commons`); `bin/db-helper` helps with DB setup.
- CI delegates to the shared workflow in `killbill/gh-actions-shared`, plus an `e2e` job running Ruby client tests against a built server.

## Architecture

Modules are one per billing domain, each exposing its public interface through the separate `killbill-api` artifact; `api/` here holds only the Guice `*Module` interfaces (`org.killbill.billing.glue.*`) that each domain implements.

- `account`, `catalog`, `subscription`, `entitlement`, `junction` (billing-events glue between entitlement/subscription and invoice), `invoice`, `payment`, `usage`, `overdue`, `tenant`, `currency` — domain modules. Each has a `glue/Default*Module` (Guice wiring), `dao/` (JDBI-based, SQL in `.sql.stg` StringTemplate files and `ddl.sql` under resources), and API implementation classes (`Default*Api`).
- `util` — shared infra: caches, audit logs, tags, custom fields, notification/bus setup, record IDs, security (Shiro), global locker. **Its test jar also provides the shared test harness and `Mock*Module`s** that other modules' tests build on.
- `jaxrs` — REST layer (`jaxrs/resources/*Resource`, JSON classes in `jaxrs/json`) over the domain APIs.
- `beatrix` — end-to-end integration tests wiring all real modules together (`BeatrixTestSuiteWithEmbeddedDB`); the best place to understand cross-module flows (subscription → billing events → invoice → payment). Slow.
- `profiles/killbill` (full server: Jetty webapp, `killbill-server.properties`) and `profiles/killpay` (payments-only profile).

Cross-cutting patterns:
- Dependency injection with Guice; each module is installed explicitly by the server's wiring, and tests swap in `Test*Module`/`Mock*Module` variants.
- Modules communicate asynchronously through the internal event bus (`killbill-queue`/`killbill-notificationq` persistent bus and notification queues, tables in DB) in addition to direct API calls; many flows (invoicing after a subscription change, payment retries, overdue) are driven by bus events or scheduled notifications rather than direct calls.
- Everything is multi-tenant and audited: calls carry a `CallContext`/`TenantContext`, and internal variants (`InternalCallContext`) carry `accountRecordId`/`tenantRecordId` — pass these through rather than constructing new ones.
- Plugins (payment, invoice, catalog, control, etc.) are invoked through the OSGI plugin APIs from `killbill-api`/`killbill-platform`; core payment code calls them via payment plugin dispatchers in `payment/`.
