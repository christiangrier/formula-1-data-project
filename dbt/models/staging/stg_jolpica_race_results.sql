with source as (select * from {{ source('silver', 'jolpica_race_results') }}),
renamed as (
    select
        season,
        round,
        driver_id,
        abbreviation,
        driver_name,
        constructor,
        race_name,
        circuit,
        date as race_date,
        grid as grid_position,
        position as finish_position,
        points,
        status,
        fastest_lap_rank

    from source
)
 
select * from renamed