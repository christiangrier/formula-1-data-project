{{
    config(
        materialized='table'
    )
}}
 
with standings as (
 
    select * from {{ ref('stg_jolpica_constructor_standings') }}
 
),
 
final as (
 
    select
        -- primary key
        {{ dbt_utils.generate_surrogate_key(['season', 'round', 'constructor_id']) }}
                                        as standing_id,
 
        -- identifiers
        season,
        round,
        constructor_id,
        constructor,
        constructor_country,
 
        -- standings
        championship_position,
        championship_points,
        wins,
 
        -- points delta from previous round
        championship_points - lag(championship_points) over (
            partition by season, constructor_id
            order by round
        )                               as points_this_round
 
    from standings
 
)
 
select * from final