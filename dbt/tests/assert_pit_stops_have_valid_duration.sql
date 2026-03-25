-- Asserts that all pit stop durations in mart_pit_stops are within a
-- physically plausible range.
--
-- Lower bound: (1.5 seconds) the fastest pit stops in F1 history are ~1.8s.
-- Upper bound: (600 seconds) a drive-through penalty or
--   prolonged stop due to an incident. 
--
-- This test returns rows that FAIL the assertion — dbt expects 0 rows.
 
select
    pit_stop_id,
    season,
    round,
    driver_id,
    pit_stop_number,
    pit_stop_duration_seconds
from {{ ref('mart_pit_stops') }}
where pit_stop_duration_seconds < 1.5
   or pit_stop_duration_seconds > 1200