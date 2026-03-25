{{
    config(
        materialized='table'
    )
}}

with standings as (

    select * from {{ ref('stg_jolpica_driver_standings') }}

),

final as (

    select
        -- primary key
        {{ dbt_utils.generate_surrogate_key(['season', 'round', 'driver_id']) }}
                                        as standing_id,

        -- identifiers
        season,
        round,
        driver_id,
        driver_code,
        driver_name,
        driver_dob,
        driver_country,
        constructor,
        constructor_country,

        -- standings
        championship_position,
        championship_points,
        wins,

        -- points delta from previous round
        championship_points - lag(championship_points) over (
            partition by season, driver_id
            order by round
        )                               as points_this_round

    from standings

)

select * from final
