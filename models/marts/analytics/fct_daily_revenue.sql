with orders as (

    select * from {{ ref('orders') }}

),

locations as (

    select * from {{ ref('locations') }}

),

daily_agg as (

    select
        o.ordered_at                                            as date_day,
        o.location_id,
        l.location_name,

        count(o.order_id)                                       as total_orders,
        sum(o.order_total)                                      as total_revenue,
        sum(o.order_cost)                                       as total_cost,
        sum(o.order_total - o.order_cost)                       as gross_profit,

        round(
            sum(o.order_total - o.order_cost)
            / nullif(sum(o.order_total), 0) * 100,
            2
        )                                                       as gross_margin_pct,

        round(sum(o.order_total) / count(o.order_id), 2)       as avg_order_value,

        sum(case when o.customer_order_number = 1 then 1 else 0 end)
                                                                as new_customer_orders,
        sum(case when o.customer_order_number > 1 then 1 else 0 end)
                                                                as returning_customer_orders,

        sum(case when o.is_food_order and not o.is_drink_order then 1 else 0 end)
                                                                as food_only_orders,
        sum(case when o.is_drink_order and not o.is_food_order then 1 else 0 end)
                                                                as drink_only_orders,
        sum(case when o.is_food_order and o.is_drink_order then 1 else 0 end)
                                                                as mixed_orders

    from orders o
    left join locations l on o.location_id = l.location_id
    group by 1, 2, 3

)

select * from daily_agg
