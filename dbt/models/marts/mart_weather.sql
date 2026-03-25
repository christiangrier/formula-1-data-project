{{
    config(
        materialized='table'
    )
}}
 
with weather as (
 
    select * from {{ ref('stg_fastf1_weather') }}
 
),
 
schedule as (
 
    select
        season,
        round,
        race_name,
        circuit,
        race_datetime,
        is_sprint_weekend
 
    from {{ ref('stg_jolpica_race_schedule') }}
 
),
 
final as (
 
    select
        -- primary key
        {{ dbt_utils.generate_surrogate_key(['weather.season', 'weather.round', 'weather.session_elapsed_seconds']) }}
                                        as weather_id,
 
        -- identifiers
        weather.season,
        weather.round,
        schedule.race_name,
        schedule.circuit,
        schedule.race_datetime,
        schedule.is_sprint_weekend,
        weather.session_elapsed_seconds,
 
        -- temperature (celsius)
        weather.air_temp,
        weather.track_temp,
 
        -- derived — track temp delta above air temp
        weather.track_temp - weather.air_temp
                                        as track_air_temp_delta,
 
        -- conditions
        weather.humidity,
        weather.pressure,
        weather.rainfall,
        weather.wind_speed,
        weather.wind_direction
 
    from weather
    left join schedule
        on  weather.season = schedule.season
        and weather.round  = schedule.round
 
)
 
select * from final