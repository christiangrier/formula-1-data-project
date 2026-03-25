with source as (

    select * from {{ source('silver', 'jolpica_constructor_standings') }}

),

renamed as (

    select
        -- identifiers
        season,
        round,
        constructor_id,
        constructor,
        constructor_country,

        -- standings
        position                as championship_position,
        points                  as championship_points,
        wins

    from source

)

select * from renamed
