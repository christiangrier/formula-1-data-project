with source as (

    select * from {{ source('silver', 'fastf1_laps') }}

),

renamed as (

    select
        -- identifiers
        season,
        round,
        abbreviation,
        driver_number,
        team,
        lap_number,
        stint,

        -- lap timing (seconds)
        lap_time_seconds,
        sector1_time_seconds,
        sector2_time_seconds,
        sector3_time_seconds,
        time_seconds            as session_elapsed_seconds,
        lap_start_time_seconds,
        pit_out_time_seconds,
        pit_in_time_seconds,

        -- sector session times (seconds)
        sector1_session_time_seconds,
        sector2_session_time_seconds,
        sector3_session_time_seconds,

        -- speed traps (km/h)
        speed_i1,
        speed_i2,
        speed_fl,
        speed_st,

        -- tyre
        compound,
        tyre_life,
        fresh_tyre,

        -- flags
        is_personal_best,
        is_accurate,
        fast_f1_generated,

        -- track
        track_status,
        position

    from source

)

select * from renamed
