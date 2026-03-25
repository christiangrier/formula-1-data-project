with source as (

    select * from {{ source('silver', 'fastf1_weather') }}

),

renamed as (

    select
        -- identifiers
        season,
        round,
        time_seconds            as session_elapsed_seconds,

        -- temperature (°C)
        air_temp,
        track_temp,

        -- conditions
        humidity,
        pressure,
        rainfall,
        wind_direction,
        wind_speed

    from source

)

select * from renamed
