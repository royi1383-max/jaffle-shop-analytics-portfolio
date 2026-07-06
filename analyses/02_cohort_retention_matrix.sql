-- ┌─────────────────────────────────────────────────────────────┐
-- │  Business Question: Do customers come back?                 │
-- │  Technique: Cohort retention matrix (pivot months 0–11)     │
-- └─────────────────────────────────────────────────────────────┘

-- Each row = one acquisition cohort
-- Each column = retention % at month N (0 = acquisition, always 100%)
-- How to read: a cell value of 94.2 at Month 3 means 94.2% of
--              customers from that cohort ordered again in month 3

select
    strftime(cohort_month, '%Y-%m')             as cohort,
    cohort_size,

    max(case when months_since_first_order = 0  then round(retention_rate * 100, 1) end) as "Month 0",
    max(case when months_since_first_order = 1  then round(retention_rate * 100, 1) end) as "Month 1",
    max(case when months_since_first_order = 2  then round(retention_rate * 100, 1) end) as "Month 2",
    max(case when months_since_first_order = 3  then round(retention_rate * 100, 1) end) as "Month 3",
    max(case when months_since_first_order = 4  then round(retention_rate * 100, 1) end) as "Month 4",
    max(case when months_since_first_order = 5  then round(retention_rate * 100, 1) end) as "Month 5",
    max(case when months_since_first_order = 6  then round(retention_rate * 100, 1) end) as "Month 6",
    max(case when months_since_first_order = 7  then round(retention_rate * 100, 1) end) as "Month 7",
    max(case when months_since_first_order = 8  then round(retention_rate * 100, 1) end) as "Month 8",
    max(case when months_since_first_order = 9  then round(retention_rate * 100, 1) end) as "Month 9",
    max(case when months_since_first_order = 10 then round(retention_rate * 100, 1) end) as "Month 10",
    max(case when months_since_first_order = 11 then round(retention_rate * 100, 1) end) as "Month 11"

from {{ ref('fct_cohorts') }}
group by 1, 2
order by 1
