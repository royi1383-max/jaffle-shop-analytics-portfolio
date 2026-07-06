-- ┌─────────────────────────────────────────────────────────────┐
-- │  Business Question: Is the business growing?                │
-- │  Technique: Week-over-week growth + 4-week moving average   │
-- └─────────────────────────────────────────────────────────────┘

with weekly as (

    select
        date_trunc('week', ordered_at)              as week_start,
        count(order_id)                             as orders,
        round(sum(order_total), 2)                  as revenue,
        round(avg(order_total), 2)                  as aov,
        count(distinct customer_id)                 as unique_customers

    from {{ ref('orders') }}
    group by 1

),

with_growth as (

    select
        week_start,
        orders,
        revenue,
        aov,
        unique_customers,

        -- Prior week for comparison
        lag(revenue, 1) over (order by week_start)  as prev_week_revenue,

        -- 4-week moving average (smooths volatility)
        avg(revenue) over (
            order by week_start
            rows between 3 preceding and current row
        )                                           as ma_4week_revenue,

        -- Week-over-week growth %
        round(
            (revenue - lag(revenue, 1) over (order by week_start))
            / nullif(lag(revenue, 1) over (order by week_start), 0) * 100,
            1
        )                                           as wow_growth_pct,

        -- Cumulative revenue (running total)
        sum(revenue) over (order by week_start)     as cumulative_revenue

    from weekly

)

select * from with_growth
order by week_start
