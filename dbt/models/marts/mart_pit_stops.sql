{{
    config(
        materialized='table'
    )
}}
 
with enriched as (
 
    select * from {{ ref('int_pit_stops_enriched') }}
 
),
 
final as (
 
    select
        -- primary key
        {{ dbt_utils.generate_surrogate_key(['season', 'round', 'driver_id', 'pit_stop_number']) }}
                                        as pit_stop_id,
 
        -- identifiers
        season,
        round,
        driver_id,
        driver_abbreviation,
        race_name,
        circuit,
        race_date,
 
        -- pit stop detail
        pit_stop_number,
        lap_pitted,
        pit_in_time,
        pit_stop_duration_seconds,
 
        -- tyre context
        stint_ending,
        compound_ending,
        compound_starting,
        tyre_age_at_pit,
 
        -- lap context
        pit_lap_time_seconds,
        pit_lap_is_accurate,
 
        -- derived — was this a short or long stop (> 30s suggests problem)
        case
            when pit_stop_duration_seconds > 30 then true
            else false
        end                             as is_slow_pit_stop
 
    from enriched
 
)
 
select * from final