with source as (
 
    select * from {{ source('silver', 'jolpica_pit_stops') }}
 
),
 
renamed as (
 
    select
        -- identifiers
        season,
        round,
        driver_id,
        race_name,
        circuit,
        date as race_date,
 
        -- pit stop detail
        stop_num as pit_stop_number,
        lap_pitted,
        pit_in_time,
        pit_stop_duration as pit_stop_duration_seconds
 
    from source
 
)
 
select * from renamed