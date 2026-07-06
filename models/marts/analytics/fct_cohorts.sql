with customers as (

    select * from {{ ref('customers') }}

),

orders as (

    select * from {{ ref('orders') }}

),

-- Each customer's acquisition month
cohort_base as (

    select
        customer_id,
        date_trunc('month', first_ordered_at) as cohort_month
    from customers
    where first_ordered_at is not null

),

-- All months a customer was active (placed at least one order)
customer_activity as (

    select distinct
        customer_id,
        date_trunc('month', ordered_at) as activity_month
    from orders

),

-- Join to compute months since first order
cohort_joined as (

    select
        c.cohort_month,
        a.activity_month,
        datediff('month', c.cohort_month, a.activity_month)    as months_since_first_order,
        c.customer_id

    from cohort_base c
    inner join customer_activity a using (customer_id)
    where a.activity_month >= c.cohort_month

),

-- Cohort size (how many customers acquired in that month)
cohort_sizes as (

    select
        cohort_month,
        count(distinct customer_id) as cohort_size
    from cohort_base
    group by 1

),

-- Active customers per cohort per activity month
cohort_activity as (

    select
        cohort_month,
        activity_month,
        months_since_first_order,
        count(distinct customer_id) as active_customers
    from cohort_joined
    group by 1, 2, 3

),

final as (

    select
        ca.cohort_month,
        ca.activity_month,
        ca.months_since_first_order,
        cs.cohort_size,
        ca.active_customers,
        round(ca.active_customers * 1.0 / cs.cohort_size, 4) as retention_rate

    from cohort_activity ca
    left join cohort_sizes cs using (cohort_month)

)

select * from final
order by cohort_month, months_since_first_order
