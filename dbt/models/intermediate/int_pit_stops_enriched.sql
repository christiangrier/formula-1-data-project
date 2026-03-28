{{
    config(
        materialized='ephemeral'
    )
}}
 
with pit_stops as (
 
    select
        season,
        round,
        driver_id,
        race_name,
        circuit,
        race_date,
        pit_stop_number,
        lap_pitted,
        pit_in_time,
        pit_stop_duration_seconds
 
    from {{ ref('stg_jolpica_pit_stops') }}
 
),
 
laps as (
 
    select
        season,
        round,
        abbreviation,
        lap_number,
        stint,
        compound,
        tyre_life,
        lap_time_seconds,
        is_accurate,
        pit_in_time_seconds,
        pit_out_time_seconds
 
    from {{ ref('stg_fastf1_laps') }}
 
),
 
-- map FastF1 driver abbreviation to Jolpica driver_id via the race spine
driver_map as (
 
    select distinct
        season,
        round,
        driver_id,
        abbreviation            as driver_abbreviation
 
    from {{ ref('stg_fastf1_results') }}
 
),
 
-- attach FastF1 abbreviation to pit stops so we can join to laps
pit_stops_with_abbrev as (
 
    select
        p.*,
        dm.driver_abbreviation
 
    from pit_stops p
    left join driver_map dm
        on  p.season    = dm.season
        and p.round     = dm.round
        and p.driver_id = dm.driver_id
 
),
 
-- get the lap the driver pitted on for compound and lap time context
pit_lap_context as (
 
    select
        p.season,
        p.round,
        p.driver_id,
        p.driver_abbreviation,
        p.race_name,
        p.circuit,
        p.race_date,
        p.pit_stop_number,
        p.lap_pitted,
        p.pit_in_time,
        p.pit_stop_duration_seconds,
 
        -- lap context from FastF1 on the lap the driver pitted
        l.stint                         as stint_ending,
        l.compound                      as compound_ending,
        l.tyre_life                     as tyre_age_at_pit,
        l.lap_time_seconds              as pit_lap_time_seconds,
        l.is_accurate                   as pit_lap_is_accurate,
 
        -- next stint compound — from the lap immediately after the pit
        lead(l.compound) over (
            partition by l.season, l.round, l.abbreviation
            order by l.lap_number
        )                               as compound_starting
 
    from pit_stops_with_abbrev p
    left join laps l
        on  p.season               = l.season
        and p.round                = l.round
        and p.driver_abbreviation  = l.abbreviation
        and p.lap_pitted           = l.lap_number
 
)
 
select * from pit_lap_context