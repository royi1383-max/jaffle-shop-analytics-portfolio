with order_items as (

    select * from {{ ref('order_items') }}

),

supplies as (

    select * from {{ ref('supplies') }}

),

-- Total supply cost per product, split by perishable vs. non-perishable
supply_breakdown as (

    select
        product_id,
        sum(supply_cost)                                        as total_supply_cost_per_unit,
        sum(case when is_perishable_supply then supply_cost else 0 end)
                                                                as perishable_cost_per_unit,
        sum(case when not is_perishable_supply then supply_cost else 0 end)
                                                                as non_perishable_cost_per_unit
    from supplies
    group by 1

),

-- Revenue and unit sales from order_items
product_sales as (

    select
        product_id,
        product_name,
        is_food_item,
        is_drink_item,
        count(order_item_id)                                    as units_sold,
        sum(product_price)                                      as total_revenue,
        sum(supply_cost)                                        as actual_supply_cost_total

    from order_items
    group by 1, 2, 3, 4

),

final as (

    select
        ps.product_id,
        ps.product_name,
        case when ps.is_food_item then 'food' else 'beverage' end  as product_type,

        ps.units_sold,
        ps.total_revenue,

        ps.actual_supply_cost_total                             as total_supply_cost,

        -- Per-unit costs from supply breakdown
        round(sb.perishable_cost_per_unit, 4)                  as perishable_cost_per_unit,
        round(sb.non_perishable_cost_per_unit, 4)              as non_perishable_cost_per_unit,

        -- Scale to total units sold
        round(sb.perishable_cost_per_unit * ps.units_sold, 2)  as total_perishable_cost,
        round(sb.non_perishable_cost_per_unit * ps.units_sold, 2)
                                                                as total_non_perishable_cost,

        -- Margin
        round(ps.total_revenue - ps.actual_supply_cost_total, 2)
                                                                as gross_profit,
        round(
            (ps.total_revenue - ps.actual_supply_cost_total)
            / nullif(ps.total_revenue, 0) * 100,
            2
        )                                                       as gross_margin_pct,

        -- Perishable exposure (what % of revenue is at risk from waste)
        round(
            sb.perishable_cost_per_unit * ps.units_sold
            / nullif(ps.total_revenue, 0) * 100,
            2
        )                                                       as perishable_pct_of_revenue

    from product_sales ps
    left join supply_breakdown sb using (product_id)

)

select * from final
order by gross_margin_pct desc
