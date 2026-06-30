---
name: dbt-model
description: Scaffold a new dbt model with staging/marts layering, schema tests, and docs for the Meridian project. Use this whenever the user asks to add, create, or scaffold a dbt model, a staging model, a mart, a fact or dimension table, or mentions dbt transformations — even if they only describe the table they want rather than saying "dbt".
---

# dbt model scaffolder (Meridian)

Create a new dbt model that follows this project's layering and testing conventions.
Default to dbt-core with the DuckDB adapter (free, local) unless the project says otherwise.

## Layering rules
- `models/staging/stg_<source>__<entity>.sql` — 1:1 with a source, renames/casts only, materialized as views.
- `models/marts/<domain>/(fct|dim)_<name>.sql` — business logic, materialized as tables.
- Never let a mart select directly from a source; it goes through staging.

## Steps
1. Ask (or infer) which layer and which Meridian entity (customer, product, order, order_item, event, payment, ticket, review).
2. Write the `.sql` using `ref()`/`source()`, never raw table names. Use CTEs, final `select`.
3. Add a sibling `_<name>.yml` with: a model description, a description per column, and tests
   (`unique` + `not_null` on the key, `relationships` for foreign keys, `accepted_values` for enums).
4. If a new source is introduced, add it to `models/staging/_sources.yml`.
5. Remind the user to run `dbt build --select <model>` and to add an `exposure` if it feeds a dashboard.

## Quality bar
Every model has a description and at least one test, or it does not ship. See
`references/model_template.sql` for the canonical SQL shape.
