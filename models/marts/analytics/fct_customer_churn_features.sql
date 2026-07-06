with customers as (

    select * from {{ ref('customers') }}

),

orders as (

    select * from {{ ref('orders') }}

),

order_items as (

    select * from {{ ref('order_items') }}

),

-- Days between consecutive orders per customer
order_gaps as (

    select
        customer_id,
        ordered_at,
        lag(ordered_at) over (
            partition by customer_id order by ordered_at
        )                                                       as prev_order_date,
        datediff(
            'day',
            lag(ordered_at) over (partition by customer_id order by ordered_at),
            ordered_at
        )                                                       as days_between_orders

    from orders

),

-- Avg and std of days between orders per customer
order_cadence as (

    select
        customer_id,
        avg(days_between_orders)                                as avg_days_between_orders,
        stddev(days_between_orders)                             as stddev_days_between_orders
    from order_gaps
    where days_between_orders is not null
    group by 1

),

-- Food vs. drink preference
product_mix as (

    select
        oi.order_id,
        o.customer_id,
        sum(case when oi.is_food_item then 1 else 0 end)       as food_items,
        sum(case when oi.is_drink_item then 1 else 0 end)       as drink_items,
        count(*)                                                as total_items
    from order_items oi
    inner join orders o using (order_id)
    group by 1, 2

),

customer_mix as (

    select
        customer_id,
        round(sum(food_items) * 1.0 / nullif(sum(total_items), 0), 4)  as food_item_pct,
        round(sum(drink_items) * 1.0 / nullif(sum(total_items), 0), 4) as drink_item_pct
    from product_mix
    group by 1

),

-- Recent vs. prior 30-day order frequency for trend signal
recency_windows as (

    select
        customer_id,
        count(case
            when datediff('day', ordered_at, (select max(ordered_at) from orders)) <= 30
            then 1
        end)                                                    as orders_last_30_days,
        count(case
            when datediff('day', ordered_at, (select max(ordered_at) from orders)) between 31 and 60
            then 1
        end)                                                    as orders_prior_30_days
    from orders
    group by 1

),

final as (

    select
        c.customer_id,
        c.customer_name,

        -- Recency / Frequency / Monetary
        datediff(
            'day',
            c.last_ordered_at,
            (select max(ordered_at) from orders)
        )                                                       as days_since_last_order,
        c.count_lifetime_orders,
        c.lifetime_spend,
        round(c.lifetime_spend / nullif(c.count_lifetime_orders, 0), 2)
                                                                as avg_order_value,

        -- Ordering cadence
        round(oc.avg_days_between_orders, 1)                    as avg_days_between_orders,
        round(oc.stddev_days_between_orders, 1)                 as stddev_days_between_orders,

        -- Product preference
        cm.food_item_pct,
        cm.drink_item_pct,

        -- Trend signal
        rw.orders_last_30_days,
        rw.orders_prior_30_days,
        rw.orders_last_30_days - rw.orders_prior_30_days       as order_frequency_trend,

        -- Churn label: no order in 90 days = churned
        datediff(
            'day',
            c.last_ordered_at,
            (select max(ordered_at) from orders)
        ) > 90                                                  as is_churned,

        c.first_ordered_at,
        c.last_ordered_at

    from customers c
    left join order_cadence oc using (customer_id)
    left join customer_mix cm using (customer_id)
    left join recency_windows rw using (customer_id)
    where c.count_lifetime_orders is not null

)

select * from final
