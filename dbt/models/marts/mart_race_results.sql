{{
    config(
        materialized='table'
    )
}}

with spine as (

    select * from {{ ref('int_race_spine') }}

),

schedule as (

    select
        season,
        round,
        is_sprint_weekend

    from {{ ref('stg_jolpica_race_schedule') }}

),

final as (

    select
        -- primary key
        {{ dbt_utils.generate_surrogate_key(['spine.season', 'spine.round', 'spine.driver_id']) }}
                                        as result_id,

        -- identifiers
        spine.season,
        spine.round,
        spine.driver_id,
        spine.driver_number,
        spine.abbreviation,
        spine.full_name,
        -- spine.country_code,
        spine.team_id,
        spine.team_name,
        spine.team_color,
        spine.constructor,

        -- race info
        spine.race_name,
        spine.circuit,
        spine.race_date,
        schedule.is_sprint_weekend,

        -- result
        spine.grid_position,
        spine.finish_position,
        spine.classified_position,
        spine.laps,
        spine.race_time_seconds,
        spine.points,
        spine.status,
        spine.fastest_lap_rank,

        -- qualifying
        -- spine.q1_seconds,
        -- spine.q2_seconds,
        -- spine.q3_seconds

    from spine
    left join schedule
        on  spine.season = schedule.season
        and spine.round  = schedule.round

)

select * from final
