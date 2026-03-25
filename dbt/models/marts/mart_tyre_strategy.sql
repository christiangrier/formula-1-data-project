{{
    config(
        materialized='table'
    )
}}

with laps as (

    select * from {{ ref('stg_fastf1_laps') }}

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

-- aggregate laps to stint level
stints as (

    select
        season,
        round,
        driver,
        stint,
        compound,
        fresh_tyre,
        min(lap_number)                 as stint_start_lap,
        max(lap_number)                 as stint_end_lap,
        count(*)                        as stint_length_laps,
        max(tyre_life)                  as tyre_age_end,

        -- pace metrics — only accurate laps for clean degradation signal
        avg(case
            when is_accurate then lap_time_seconds
        end)                            as avg_lap_time_seconds,

        min(case
            when is_accurate then lap_time_seconds
        end)                            as fastest_lap_seconds,

        -- degradation rate: slope of lap time over tyre life
        -- positive value = getting slower per lap (deg)
        regr_slope(lap_time_seconds, tyre_life)
                                        as degradation_rate_seconds_per_lap

    from laps
    where lap_time_seconds is not null
    group by
        season,
        round,
        driver,
        stint,
        compound,
        fresh_tyre

),

final as (

    select
        -- primary key
        {{ dbt_utils.generate_surrogate_key(['stints.season', 'stints.round', 'stints.driver', 'stints.stint']) }}
                                        as tyre_stint_id,

        -- identifiers
        stints.season,
        stints.round,
        stints.driver,
        di.driver_id,
        di.full_name,
        di.team_id,
        di.team_name,
        di.team_color,

        -- stint detail
        stints.stint,
        stints.compound,
        stints.fresh_tyre,
        stints.stint_start_lap,
        stints.stint_end_lap,
        stints.stint_length_laps,
        stints.tyre_age_end,

        -- pace
        stints.avg_lap_time_seconds,
        stints.fastest_lap_seconds,
        stints.degradation_rate_seconds_per_lap

    from stints
    left join driver_info di
        on  stints.season = di.season
        and stints.round  = di.round
        and stints.driver = di.abbreviation

)

select * from final
