-- ┌─────────────────────────────────────────────────────────────┐
-- │  Business Question: Which products to push vs. reconsider?  │
-- │  Technique: BCG Matrix (revenue vs. margin quadrants)       │
-- └─────────────────────────────────────────────────────────────┘

-- Stars       → high revenue, high margin   → protect & invest
-- Cash Cows   → high revenue, low margin    → optimize costs
-- Question ?  → low revenue, high margin    → grow or bundle
-- Dogs        → low revenue, low margin     → review / cut

with product_stats as (

    select
        product_id,
        product_name,
        product_type,
        units_sold,
        total_revenue,
        gross_margin_pct,
        perishable_pct_of_revenue,
        round(total_revenue / nullif(units_sold, 0), 2)  as avg_unit_price

    from {{ ref('fct_supply_cogs') }}

),

medians as (

    select
        median(total_revenue)       as median_revenue,
        median(gross_margin_pct)    as median_margin

    from product_stats

),

classified as (

    select
        p.product_id,
        p.product_name,
        p.product_type,
        p.units_sold,
        round(p.total_revenue, 0)               as total_revenue,
        p.gross_margin_pct,
        p.perishable_pct_of_revenue,
        p.avg_unit_price,
        m.median_revenue,
        m.median_margin,

        case
            when p.total_revenue > m.median_revenue
                 and p.gross_margin_pct > m.median_margin  then 'Star'
            when p.total_revenue > m.median_revenue
                 and p.gross_margin_pct <= m.median_margin then 'Cash Cow'
            when p.total_revenue <= m.median_revenue
                 and p.gross_margin_pct > m.median_margin  then 'Question Mark'
            else 'Dog'
        end                                     as bcg_quadrant,

        -- Composite score (weighted revenue + margin)
        round(
            (p.total_revenue / m.median_revenue * 0.5)
            + (p.gross_margin_pct / m.median_margin * 0.5),
            2
        )                                       as composite_score

    from product_stats p
    cross join medians m

)

select * from classified
order by composite_score desc
