import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Influencer Campaign Dashboard", layout="wide")

# ---------------------------
# Data Loader
# ---------------------------
@st.cache_data
def load_data():
    influencers = pd.read_csv('data/influencers.csv')
    posts = pd.read_csv('data/posts.csv', parse_dates=['date'])
    tracking = pd.read_csv('data/tracking.csv', parse_dates=['date'])
    payouts = pd.read_csv('data/payouts.csv')
    return influencers, posts, tracking, payouts


# ---------------------------
# KPI Calculations
# ---------------------------
def calculate_roas(tracking_f, payouts):
    total_rev = tracking_f['revenue'].sum()
    total_orders = tracking_f['orders'].sum()
    total_spend = payouts['total_payout'].sum()
    roas = total_rev / total_spend if total_spend else 0
    return total_rev, total_orders, total_spend, roas


def calculate_iroas(tracking_f, payouts):
    organic = tracking_f[tracking_f['source'] == 'organic']
    baseline = organic.groupby('product').agg(
        org_users=('user_id', 'nunique'),
        org_revenue=('revenue', 'sum')
    ).reset_index()
    baseline['rev_per_user'] = baseline['org_revenue'] / baseline['org_users']

    inf_perf = tracking_f[tracking_f['source'] == 'influencer'].groupby(
        ['influencer_id', 'product']
    ).agg(
        inf_users=('user_id', 'nunique'),
        inf_revenue=('revenue', 'sum')
    ).reset_index()

    inf_perf = inf_perf.merge(baseline[['product', 'rev_per_user']], on='product', how='left')
    inf_perf['expected_baseline_rev'] = inf_perf['rev_per_user'] * inf_perf['inf_users']
    inf_perf['incremental_revenue'] = inf_perf['inf_revenue'] - inf_perf['expected_baseline_rev']

    inf_spend = payouts[['influencer_id', 'total_payout']]
    inf_perf = inf_perf.merge(inf_spend, on='influencer_id', how='left')
    inf_perf['iROAS'] = inf_perf['incremental_revenue'] / (inf_perf['total_payout'] + 1e-9)

    overall_iroas = inf_perf['iROAS'].mean()
    return inf_perf, overall_iroas


# ---------------------------
# Top Influencers Table
# ---------------------------
def get_top_influencers(tracking_f, posts_f, payouts, influencers, top_n):
    top_inf = (
        tracking_f[tracking_f['source'] == 'influencer']
        .groupby('influencer_id')
        .agg(
            revenue=('revenue', 'sum'),
            orders=('orders', 'sum')
        )
        .reset_index()
        .merge(influencers, left_on='influencer_id', right_on='id')
    )

    post_metrics = posts_f.groupby('influencer_id').agg(
        total_likes=('likes', 'sum'),
        total_comments=('comments', 'sum'),
        total_reach=('reach', 'sum')
    ).reset_index()
    post_metrics['engagement_rate'] = (
        (post_metrics['total_likes'] + post_metrics['total_comments']) / post_metrics['total_reach']
    )

    top_inf = top_inf.merge(post_metrics[['influencer_id', 'engagement_rate']], on='influencer_id', how='left')
    top_inf = top_inf.merge(payouts[['influencer_id', 'total_payout']], on='influencer_id', how='left')
    top_inf['cost_per_order'] = top_inf['total_payout'] / (top_inf['orders'] + 1e-9)

    return top_inf.sort_values('revenue', ascending=False).head(top_n)


# ---------------------------
# Main App
# ---------------------------
influencers, posts, tracking, payouts = load_data()

# Sidebar Filters
st.sidebar.header("Filters")
start_date, end_date = st.sidebar.date_input(
    "Date range",
    [tracking['date'].min(), tracking['date'].max()]
)
platform_filter = st.sidebar.multiselect(
    "Platform", influencers['platform'].unique(), influencers['platform'].unique()
)
category_filter = st.sidebar.multiselect(
    "Category", influencers['category'].unique(), influencers['category'].unique()
)
top_n = st.sidebar.slider("Show Top N Influencers", min_value=5, max_value=20, value=10)

# Filter Tracking
tracking_f = tracking[
    (tracking['date'] >= pd.to_datetime(start_date)) &
    (tracking['date'] <= pd.to_datetime(end_date))
].merge(
    influencers[['id', 'platform', 'category']],
    left_on='influencer_id',
    right_on='id',
    how='left'
)
tracking_f = tracking_f[
    (tracking_f['platform'].isin(platform_filter)) &
    (tracking_f['category'].isin(category_filter))
]

# Filter Posts
posts_f = posts[
    (posts['date'] >= pd.to_datetime(start_date)) &
    (posts['date'] <= pd.to_datetime(end_date))
].merge(
    influencers[['id', 'category']],
    left_on='influencer_id',
    right_on='id',
    how='left'
)
posts_f = posts_f[
    (posts_f['platform'].isin(platform_filter)) &
    (posts_f['category'].isin(category_filter))
]

# KPIs
total_rev, total_orders, total_spend, roas = calculate_roas(tracking_f, payouts)
inf_perf, overall_iroas = calculate_iroas(tracking_f, payouts)

# KPI Display
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Revenue", f"₹{total_rev:,.0f}")
col2.metric("Orders", f"{total_orders:,}")
col3.metric("Spend", f"₹{total_spend:,.0f}")
col4.metric("ROAS", f"{roas:.2f}")
col5.metric("Avg iROAS", f"{overall_iroas:.2f}")

# Top Influencers
top_inf = get_top_influencers(tracking_f, posts_f, payouts, influencers, top_n)
st.subheader(f"Top {top_n} Influencers by Revenue")

# Conditional Formatting
def highlight_cells(val, good_thresh=0.3, bad_thresh=0.1):
    color = ""
    if isinstance(val, (float, int)):
        if val >= good_thresh:
            color = 'background-color: #d4edda'  # green
        elif val <= bad_thresh:
            color = 'background-color: #f8d7da'  # red
    return color

styled_top_inf = top_inf[['name', 'platform', 'category', 'revenue', 'orders', 'engagement_rate', 'cost_per_order']].style.applymap(
    lambda x: highlight_cells(x, good_thresh=0.05, bad_thresh=0.02), subset=['engagement_rate']
)

st.dataframe(styled_top_inf, use_container_width=True)

csv_export = top_inf.to_csv(index=False)
st.download_button(
    label="📥 Download Table as CSV",
    data=csv_export,
    file_name="top_influencers.csv",
    mime="text/csv"
)

# Revenue Over Time Chart
rev_time = tracking_f.groupby('date')['revenue'].sum().reset_index()
chart = alt.Chart(rev_time).mark_line(point=True).encode(
    x='date:T',
    y='revenue:Q',
    tooltip=['date:T', 'revenue:Q']
).properties(width=800, height=300)
st.altair_chart(chart)

# iROAS Table
st.subheader("Incremental ROAS by Influencer")
iroas_table = (
    inf_perf.groupby('influencer_id').agg(
        total_incremental_rev=('incremental_revenue', 'sum'),
        spend=('total_payout', 'mean'),
        iROAS=('iROAS', 'mean')
    ).reset_index()
    .merge(influencers, left_on='influencer_id', right_on='id')
    [['name', 'category', 'platform', 'total_incremental_rev', 'spend', 'iROAS']]
    .sort_values('iROAS', ascending=False)
)
styled_iroas = iroas_table.style.applymap(
    lambda x: highlight_cells(x, good_thresh=2, bad_thresh=1), subset=['iROAS']
)
st.dataframe(styled_iroas, use_container_width=True)

csv_iroas = iroas_table.to_csv(index=False)
st.download_button(
    label="📥 Download iROAS Table as CSV",
    data=csv_iroas,
    file_name="iroas_table.csv",
    mime="text/csv"
)
