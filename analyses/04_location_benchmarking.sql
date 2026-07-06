-- ┌─────────────────────────────────────────────────────────────┐
-- │  Business Question: Are locations performing equally?       │
-- │  Technique: Age-normalized benchmarking + trend analysis    │
-- └─────────────────────────────────────────────────────────────┘

with monthly_by_location as (

    select
        date_trunc('month', o.ordered_at)       as month,
        l.location_id,
        l.location_name,
        l.opened_date,
        count(o.order_id)                       as orders,
        round(sum(o.order_total), 2)            as revenue,
        round(avg(o.order_total), 2)            as aov,
        count(distinct o.customer_id)           as unique_customers,

        -- Month number since location opened (for trend comparison)
        datediff(
            'month',
            l.opened_date,
            date_trunc('month', o.ordered_at)
        )                                       as months_since_open

    from {{ ref('orders') }} o
    left join {{ ref('locations') }} l using (location_id)
    group by 1, 2, 3, 4

),

with_growth as (

    select
        *,

        -- MoM revenue growth per location
        lag(revenue, 1) over (
            partition by location_id order by month
        )                                       as prev_month_revenue,

        round(
            (revenue - lag(revenue, 1) over (partition by location_id order by month))
            / nullif(lag(revenue, 1) over (partition by location_id order by month), 0) * 100,
            1
        )                                       as mom_growth_pct,

        -- 3-month moving average per location
        avg(revenue) over (
            partition by location_id
            order by month
            rows between 2 preceding and current row
        )                                       as ma_3month_revenue,

        -- Rank vs. other locations in the same month
        rank() over (
            partition by month
            order by revenue desc
        )                                       as monthly_revenue_rank

    from monthly_by_location

)

select * from with_growth
order by location_name, month
