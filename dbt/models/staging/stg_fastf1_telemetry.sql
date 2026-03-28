with source as (

    select * from {{ source('silver', 'fastf1_telemetry') }}

),

renamed as (

    select
        -- identifiers
        season,
        round,
        abbreviation,
        team,
        lap_number,
        date                    as telemetry_timestamp,

        -- timing (seconds)
        session_time_seconds    as session_elapsed_seconds,
        lap_time_seconds,

        -- car state
        rpm,
        speed,
        n_gear,
        throttle,
        brake,
        drs,

        -- position on track
        distance,
        relative_distance,
        x,
        y,
        z,

        -- context
        driver_ahead,
        distance_to_driver_ahead,
        status                  as track_status

    from source

)

select * from renamed
