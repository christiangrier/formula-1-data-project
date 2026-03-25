{{
    config(
        materialized='table'
    )
}}

with stints as (

    select * from {{ ref('int_telemetry_stints') }}

),

driver_info as (

    select distinct
        season,
        round,
        abbreviation,
        driver_id,
        full_name,
        team_id,
        team_name,
        team_color

    from {{ ref('stg_fastf1_results') }}

),

final as (

    select
        -- primary key
        {{ dbt_utils.generate_surrogate_key(['stints.season', 'stints.round', 'stints.driver', 'stints.stint']) }}
                                        as telemetry_stint_id,

        -- identifiers
        stints.season,
        stints.round,
        stints.driver,
        di.driver_id,
        di.full_name,
        di.team_id,
        di.team_name,
        di.team_color,

        -- stint context
        stints.stint,
        stints.compound,
        stints.fresh_tyre,
        stints.stint_laps,
        stints.tyre_age_start,
        stints.tyre_age_end,

        -- speed metrics (km/h)
        stints.avg_speed,
        stints.max_speed,
        stints.min_speed_on_throttle,

        -- throttle and braking
        stints.avg_throttle,
        stints.full_throttle_pct,
        stints.brake_pct,

        -- drs and gear
        stints.drs_open_pct,
        stints.avg_gear,

        -- distance
        stints.max_distance_metres

    from stints
    left join driver_info di
        on  stints.season = di.season
        and stints.round  = di.round
        and stints.driver = di.abbreviation

)

select * from final
