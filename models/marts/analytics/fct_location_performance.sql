with orders as (

    select * from {{ ref('orders') }}

),

locations as (

    select * from {{ ref('locations') }}

),

location_totals as (

    select
        o.location_id,
        l.location_name,
        l.opened_date,

        -- Age of the location in months
        datediff('month', l.opened_date, max(o.ordered_at))    as months_open,

        count(o.order_id)                                       as total_orders,
        sum(o.order_total)                                      as total_revenue,
        sum(o.order_cost)                                       as total_cost,
        sum(o.order_total - o.order_cost)                       as total_gross_profit,

        round(sum(o.order_total) / count(o.order_id), 2)       as avg_order_value,

        -- Normalized by age
        round(sum(o.order_total) / nullif(
            datediff('month', l.opened_date, max(o.ordered_at)), 0
        ), 2)                                                   as revenue_per_month_open,

        -- Customer mix
        round(
            sum(case when o.customer_order_number = 1 then 1 else 0 end)
            * 1.0 / count(o.order_id),
            4
        )                                                       as new_customer_order_pct,

        -- Product type mix
        round(
            sum(case when o.is_food_order and not o.is_drink_order then o.order_total else 0 end)
            / nullif(sum(o.order_total), 0),
            4
        )                                                       as food_revenue_pct,

        round(
            sum(case when o.is_drink_order and not o.is_food_order then o.order_total else 0 end)
            / nullif(sum(o.order_total), 0),
            4
        )                                                       as drink_revenue_pct

    from orders o
    left join locations l using (location_id)
    group by 1, 2, 3

),

with_rank as (

    select
        *,
        rank() over (order by total_revenue desc)              as revenue_rank,
        rank() over (order by revenue_per_month_open desc)     as efficiency_rank

    from location_totals

)

select * from with_rank
order by revenue_rank
