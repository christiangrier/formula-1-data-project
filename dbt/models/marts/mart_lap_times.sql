{{
    config(
        materialized='table'
    )
}}
 
with laps as (
 
    select * from {{ ref('stg_fastf1_laps') }}
 
),
 
-- driver map to enrich with full name and team color for dashboard use
driver_info as (
 
    select distinct
        season,
        round,
        driver_id,
        abbreviation,
        full_name,
        team_id,
        team_name,
        team_color
 
    from {{ ref('stg_fastf1_results') }}
 
),
 
final as (
 
    select
        -- primary key
        {{ dbt_utils.generate_surrogate_key(['laps.season', 'laps.round', 'laps.abbreviation', 'laps.lap_number']) }}
                                        as lap_id,
 
        -- identifiers
        laps.season,
        laps.round,
        laps.abbreviation,
        di.driver_id,
        di.full_name,
        di.team_id,
        di.team_name,
        di.team_color,
        laps.lap_number,
        laps.stint,
 
        -- lap timing (seconds)
        laps.lap_time_seconds,
        laps.sector1_time_seconds,
        laps.sector2_time_seconds,
        laps.sector3_time_seconds,
 
        -- speed traps (km/h)
        laps.speed_i1,
        laps.speed_i2,
        laps.speed_fl,
        laps.speed_st,
 
        -- tyre info
        laps.compound,
        laps.tyre_life,
        laps.fresh_tyre,
 
        -- lap flags
        -- laps.is_accurate,
        -- laps.is_personal_best,
        -- laps.deleted,
        -- laps.deleted_reason,
 
        -- track conditions
        laps.track_status,
        laps.position as track_position,
 
        -- pit timing
        laps.pit_out_time_seconds,
        laps.pit_in_time_seconds
 
    from laps
    left join driver_info di
        on  laps.season = di.season
        and laps.round  = di.round
        and laps.abbreviation = di.abbreviation
 
)
 
select * from final