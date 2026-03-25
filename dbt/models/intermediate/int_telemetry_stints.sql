{{
    config(
        materialized='ephemeral'
    )
}}
 
with laps as (
 
    select
        season,
        round,
        driver,
        lap_number,
        stint,
        compound,
        tyre_life,
        fresh_tyre
 
    from {{ ref('stg_fastf1_laps') }}
 
),
 
telemetry as (
 
    select
        season,
        round,
        driver,
        lap_number,
        speed,
        throttle,
        brake,
        drs,
        n_gear,
        distance
 
    from {{ ref('stg_fastf1_telemetry') }}
 
),
 
-- enrich telemetry with stint and compound context from laps
telemetry_enriched as (
 
    select
        t.season,
        t.round,
        t.driver,
        t.lap_number,
        l.stint,
        l.compound,
        l.tyre_life,
        l.fresh_tyre,
        t.speed,
        t.throttle,
        t.brake,
        t.drs,
        t.n_gear,
        t.distance
 
    from telemetry t
    left join laps l
        on  t.season     = l.season
        and t.round      = l.round
        and t.driver     = l.driver
        and t.lap_number = l.lap_number
 
),
 
-- aggregate to one row per driver per stint
stint_aggregated as (
 
    select
        season,
        round,
        driver,
        stint,
        compound,
        fresh_tyre,
 
        -- stint length
        count(distinct lap_number)              as stint_laps,
        max(tyre_life)                          as tyre_age_end,
        min(tyre_life)                          as tyre_age_start,
 
        -- speed metrics (km/h)
        round(avg(speed), 3)                    as avg_speed,
        max(speed)                              as max_speed,
        round(min(case
            when speed > 0 then speed
        end), 3)                                as min_speed_on_throttle,
 
        -- throttle (0–100%)
        round(avg(throttle), 3)                 as avg_throttle,
        round(avg(case
            when throttle >= 99 then 1.0
            else 0.0
        end) * 100, 3)                          as full_throttle_pct,
 
        -- braking
        round(avg(case
            when brake then 1.0
            else 0.0
        end) * 100, 3)                          as brake_pct,
 
        -- drs usage — open when drs in (10, 12, 14)
        round(avg(case
            when drs in (10, 12, 14) then 1.0
            else 0.0
        end) * 100, 3)                          as drs_open_pct,
 
        -- gear distribution
        round(avg(n_gear), 3)                   as avg_gear,
 
        -- distance coverage
        max(distance)                           as max_distance_metres
 
    from telemetry_enriched
    where stint is not null
 
    group by
        season,
        round,
        driver,
        stint,
        compound,
        fresh_tyre
 
)
 
select * from stint_aggregated