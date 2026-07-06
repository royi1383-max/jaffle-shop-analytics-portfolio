-- ┌─────────────────────────────────────────────────────────────┐
-- │  Business Question: Who are our most valuable customers?    │
-- │  Technique: RFM Segmentation (Recency, Frequency, Monetary) │
-- └─────────────────────────────────────────────────────────────┘

-- Each customer gets a score 1–5 on each dimension.
-- Combined score drives segment label and marketing action.

with rfm_raw as (

    select
        customer_id,
        customer_name,
        days_since_last_order       as recency_days,     -- lower = better
        count_lifetime_orders       as frequency,        -- higher = better
        lifetime_spend              as monetary          -- higher = better

    from {{ ref('fct_customer_churn_features') }}
    where count_lifetime_orders is not null

),

rfm_scored as (

    select
        *,

        -- Score 5 = best, 1 = worst for each dimension
        -- Recency: fewer days = score 5
        ntile(5) over (order by recency_days desc)   as r_score,
        -- Frequency: more orders = score 5
        ntile(5) over (order by frequency asc)       as f_score,
        -- Monetary: more spend = score 5
        ntile(5) over (order by monetary asc)        as m_score

    from rfm_raw

),

segmented as (

    select
        *,
        r_score + f_score + m_score                  as rfm_total,

        case
            when r_score >= 4 and f_score >= 4                   then 'Champions'
            when r_score >= 3 and f_score >= 3                   then 'Loyal Customers'
            when r_score >= 4 and f_score < 3                    then 'Recent Customers'
            when r_score between 2 and 3 and f_score >= 3        then 'At Risk'
            when r_score < 2 and f_score >= 3                    then 'Cannot Lose Them'
            when r_score < 2 and f_score < 2                     then 'Lost'
            else 'Potential Loyalists'
        end                                          as rfm_segment,

        -- Recommended action per segment
        case
            when r_score >= 4 and f_score >= 4
                then 'Reward with loyalty program, upsell premium items'
            when r_score >= 3 and f_score >= 3
                then 'Offer early access to new menu items'
            when r_score >= 4 and f_score < 3
                then 'Onboarding campaign, highlight popular products'
            when r_score between 2 and 3 and f_score >= 3
                then 'Win-back email with personalized discount'
            when r_score < 2 and f_score >= 3
                then 'Aggressive re-engagement offer (free item)'
            when r_score < 2 and f_score < 2
                then 'Survey to understand churn reason'
            else 'Nurture with regular content and mild offers'
        end                                          as recommended_action

    from rfm_scored

)

select * from segmented
order by rfm_total desc, monetary desc
