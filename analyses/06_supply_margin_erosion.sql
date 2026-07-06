-- ┌─────────────────────────────────────────────────────────────┐
-- │  Business Question: Where is margin at risk?                │
-- │  Technique: Perishable cost % trend + MoM cost inflation    │
-- └─────────────────────────────────────────────────────────────┘

with monthly_product as (

    select
        date_trunc('month', ordered_at)             as month,
        product_id,
        product_name,
        is_food_item,
        sum(product_price)                          as revenue,
        sum(supply_cost)                            as supply_cost,
        count(order_item_id)                        as units_sold

    from {{ ref('order_items') }}
    group by 1, 2, 3, 4

),

with_perishable as (

    select
        mp.*,

        -- Perishable cost per unit (from supply breakdown)
        sc.perishable_cost_per_unit,
        sc.non_perishable_cost_per_unit,

        -- Total perishable cost this month
        round(sc.perishable_cost_per_unit * mp.units_sold, 2)
                                                    as monthly_perishable_cost,

        -- Gross margin this month
        round(mp.revenue - mp.supply_cost, 2)       as gross_profit,
        round(
            (mp.revenue - mp.supply_cost) / nullif(mp.revenue, 0) * 100,
            1
        )                                           as gross_margin_pct,

        -- Perishable cost as % of revenue (waste exposure)
        round(
            sc.perishable_cost_per_unit * mp.units_sold
            / nullif(mp.revenue, 0) * 100,
            1
        )                                           as perishable_pct_of_revenue

    from monthly_product mp
    left join {{ ref('fct_supply_cogs') }} sc using (product_id)

),

with_mom_trend as (

    select
        *,

        -- MoM change in gross margin %
        gross_margin_pct
        - lag(gross_margin_pct, 1) over (
            partition by product_id order by month
        )                                           as margin_mom_change_pts,

        -- Is margin trending down? (3-month trend)
        case
            when gross_margin_pct
                 < avg(gross_margin_pct) over (
                     partition by product_id
                     order by month
                     rows between 3 preceding and 1 preceding
                 )
            then true
            else false
        end                                         as is_margin_declining,

        -- Revenue rank per month (to flag underperforming high-cost products)
        rank() over (
            partition by month
            order by perishable_pct_of_revenue desc
        )                                           as perishable_risk_rank

    from with_perishable

)

select * from with_mom_trend
order by month desc, perishable_risk_rank
