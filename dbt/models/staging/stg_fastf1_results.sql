with source as (

    select * from {{ source('silver', 'fastf1_results') }}

),

renamed as (

    select
        -- identifiers
        season,
        round,
        driver_id,
        driver_number,
        broadcast_name,
        abbreviation,
        first_name,
        last_name,
        full_name,
        country_code,
        team_id,
        team_name,
        team_color,

        -- result
        grid_position,
        position                as finish_position,
        classified_position,
        laps,
        status,
        points,

        -- race time
        time_seconds            as race_time_seconds,

        -- qualifying times (null for non-qualifying sessions)
        q1_seconds,
        q2_seconds,
        q3_seconds

    from source

)

select * from renamed
