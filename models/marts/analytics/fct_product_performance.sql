with order_items as (

    select * from {{ ref('order_items') }}

),

monthly_agg as (

    select
        product_id,
        product_name,
        is_food_item,
        is_drink_item,
        date_trunc('month', ordered_at)                         as month,

        count(order_item_id)                                    as units_sold,
        sum(product_price)                                      as total_revenue,
        sum(supply_cost)                                        as total_supply_cost,
        sum(product_price - supply_cost)                        as gross_profit,
        round(
            sum(product_price - supply_cost)
            / nullif(sum(product_price), 0) * 100,
            2
        )                                                       as gross_margin_pct,
        round(sum(product_price) / count(order_item_id), 2)    as avg_revenue_per_unit

    from order_items
    where ordered_at is not null
    group by 1, 2, 3, 4, 5

),

with_rank as (

    select
        *,
        rank() over (
            partition by month
            order by total_revenue desc
        )                                                       as revenue_rank_in_month

    from monthly_agg

)

select * from with_rank
order by month desc, revenue_rank_in_month
