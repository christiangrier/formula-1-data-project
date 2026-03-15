# Formula 1 Data Project

## Project overview

This is an end to end data portfolio project built around Formula 1 data. It covers
three disciplines: Data Engineering, Data Analytics, and Data Science

The project is built in two stages:
- **Stage 1 (local):** All logic is built and validated locally using Python, DuckDB,
  and dbt-duckdb.
- **Stage 2 (cloud):** Once logic is proven, everything migrates to Databricks on AWS.
  PySpark replaces pandas, the dbt adapter switches from DuckDB to Databricks SQL,
  and MLflow moves from local tracking to the Databricks-managed registry.

## Analytics

### Theme 1: Driver performance
**Primary question:** How do drivers compare on pure pace, consistency, and
racecraft across a season?

### Theme 2: Team and constructor analysis
**Primary question:** Which teams are the most operationally excellent, and
how has constructor competitiveness shifted across seasons?

### Theme 3: Circuit characteristics
**Primary question:** What makes each circuit unique in terms of how it
rewards certain car characteristics and driving styles?

### Theme 4: Race strategy analysis
**Primary question:** How do pit stop timing and tyre compound choices affect
race outcomes, and which teams call strategy best?

### Theme 5: Historical trends
**Primary question:** How has Formula 1 changed over the decades in terms of
competitiveness, dominant teams, and race outcomes?


## ML models

### 1. Race outcome predictor
**Primary target:** Finishing position bracket (P1–3, P4–10, P11+)
### 2. Tyre degradation model
**Primary target:** Lap time delta per lap on a given compound
### 3. Driver style clustering
**Primary target:** Finding driving style similarities 