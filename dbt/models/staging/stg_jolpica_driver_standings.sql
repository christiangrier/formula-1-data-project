with source as (

    select * from {{ source('silver', 'jolpica_driver_standings') }}

),

renamed as (

    select
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
        position                as championship_position,
        points                  as championship_points,
        wins

    from source

)

select * from renamed
