with source as (

    select * from {{ source('silver', 'jolpica_race_schedule') }}

),

renamed as (

    select
        -- identifiers
        season,
        round,
        race_name,
        circuit,

        -- session datetimes (UTC)
        race_datetime,
        fp1_datetime,
        fp2_datetime,
        fp3_datetime,
        sprint_qualy_datetime,
        qualy_datetime,

        -- sprint flag — true if this is a sprint weekend
        case
            when sprint_qualy_datetime is not null then true
            else false
        end                     as is_sprint_weekend

    from source

)

select * from renamed
