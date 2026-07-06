with customers as (

    select * from {{ ref('customers') }}

),

orders as (

    select * from {{ ref('orders') }}

),

order_items as (

    select * from {{ ref('order_items') }}

),

-- Hold back the last 30 days of the dataset as a real, observable "future"
-- window. Customers here order every ~3-6 days on average, so measuring
-- recency/churn against the very edge of the dataset (as the previous
-- version did) makes almost everyone look "active" by construction —
-- there's no time left for anyone to go quiet before the data just ends.
-- A holdout window lets us check who *actually* stopped ordering.
bounds as (

    select
        max(ordered_at)                            as dataset_end,
        max(ordered_at) - interval 30 day          as cutoff_date
    from orders

),

-- Orders known "as of" the cutoff date — this is the train-time view used
-- for every feature below, so nothing here leaks information from the
-- holdout window we're trying to predict.
train_orders as (

    select o.*
    from orders o, bounds b
    where o.ordered_at <= b.cutoff_date

),

train_order_items as (

    select oi.*
    from order_items oi
    inner join train_orders o using (order_id)

),

-- Per-customer lifetime stats, computed only from the train window
customer_train_summary as (

    select
        customer_id,
        count(distinct order_id)   as count_lifetime_orders,
        min(ordered_at)            as first_ordered_at,
        max(ordered_at)            as last_ordered_at,
        sum(order_total)           as lifetime_spend
    from train_orders
    group by 1

),

-- Days between consecutive orders per customer (train window only)
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

    from train_orders

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
    from train_order_items oi
    inner join train_orders o using (order_id)
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

-- Recent vs. prior 30-day order frequency for trend signal, measured
-- relative to the cutoff date (not the true end of the dataset)
recency_windows as (

    select
        customer_id,
        count(case
            when datediff('day', ordered_at, (select cutoff_date from bounds)) <= 30
            then 1
        end)                                                    as orders_last_30_days,
        count(case
            when datediff('day', ordered_at, (select cutoff_date from bounds)) between 31 and 60
            then 1
        end)                                                    as orders_prior_30_days
    from train_orders
    group by 1

),

-- Did the customer place ANY order in the holdout window (the real future
-- we're checking against)? If not, they churned.
holdout_activity as (

    select distinct customer_id
    from orders o, bounds b
    where o.ordered_at > b.cutoff_date

),

final as (

    select
        c.customer_id,
        c.customer_name,

        -- Recency / Frequency / Monetary, all as of the cutoff date
        datediff(
            'day',
            cs.last_ordered_at,
            (select cutoff_date from bounds)
        )                                                       as days_since_last_order,
        cs.count_lifetime_orders,
        cs.lifetime_spend,
        round(cs.lifetime_spend / nullif(cs.count_lifetime_orders, 0), 2)
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

        -- Churn label: no order at all in the 30-day holdout window
        -- following the cutoff date
        (ha.customer_id is null)                               as is_churned,

        cs.first_ordered_at,
        cs.last_ordered_at

    from customers c
    inner join customer_train_summary cs using (customer_id)
    left join order_cadence oc using (customer_id)
    left join customer_mix cm using (customer_id)
    left join recency_windows rw using (customer_id)
    left join holdout_activity ha using (customer_id)

)

select * from final
