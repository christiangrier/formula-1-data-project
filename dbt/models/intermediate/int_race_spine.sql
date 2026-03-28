{{
    config(
        materialized='ephemeral'
    )
}}
 
with fastf1 as (
 
    select
        season,
        round,
        driver_id,
        driver_number,
        abbreviation,
        first_name,
        last_name,
        full_name,
        -- country_code,
        team_id,
        team_name,
        team_color,
        grid_position,
        finish_position,
        classified_position,
        laps,
        points                  as fastf1_points,
        status                  as fastf1_status,
        race_time_seconds,
        -- q1_seconds,
        -- q2_seconds,
        -- q3_seconds
 
    from {{ ref('stg_fastf1_results') }}
 
),
 
jolpica as (
 
    select
        season,
        round,
        driver_id,
        constructor,
        race_name,
        circuit,
        race_date,
        finish_position         as jolpica_finish_position,
        points                  as jolpica_points,
        status                  as jolpica_status,
        fastest_lap_rank
 
    from {{ ref('stg_jolpica_race_results') }}
 
),
 
joined as (
 
    select
        -- identifiers
        fastf1.season,
        fastf1.round,
        fastf1.driver_id,
        fastf1.driver_number,
        fastf1.abbreviation,
        fastf1.first_name,
        fastf1.last_name,
        fastf1.full_name,
        -- fastf1.country_code,
        fastf1.team_id,
        fastf1.team_name,
        fastf1.team_color,
 
        -- race info from Jolpica (authoritative for schedule metadata)
        jolpica.race_name,
        jolpica.circuit,
        jolpica.race_date,
        jolpica.constructor,
 
        -- result — FastF1 is authoritative for positions and timing
        fastf1.grid_position,
        fastf1.finish_position,
        fastf1.classified_position,
        fastf1.laps,
        fastf1.race_time_seconds,
 
        -- points — use Jolpica as authoritative (more historically complete)
        jolpica.jolpica_points   as points,
 
        -- status — coalesce both sources, FastF1 preferred
        coalesce(
            fastf1.fastf1_status,
            jolpica.jolpica_status
        )                        as status,
 
        -- fastest lap — only available from Jolpica
        jolpica.fastest_lap_rank,
 
        -- qualifying times
        -- fastf1.q1_seconds,
        -- fastf1.q2_seconds,
        -- fastf1.q3_seconds
 
    from fastf1
    left join jolpica
        on  fastf1.season    = jolpica.season
        and fastf1.round     = jolpica.round
        and fastf1.driver_id = jolpica.driver_id
 
)
 
select * from joined