import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

np.random.seed(42)
os.makedirs("data", exist_ok=True)

# -------------------------------
# 1) Influencers table
# -------------------------------
n_inf = 20
inf_ids = np.arange(1, n_inf + 1)

influencers = pd.DataFrame({
    'id': inf_ids,
    'name': [f'Influencer_{i}' for i in inf_ids],
    'category': np.random.choice(['Fitness', 'Nutrition', 'Lifestyle', 'Wellness'], n_inf),
    'gender': np.random.choice(['M', 'F'], n_inf),
    'follower_count': np.random.randint(10_000, 2_000_000, n_inf),
    'platform': np.random.choice(['Instagram', 'YouTube', 'Twitter'], n_inf)
})
influencers.to_csv('data/influencers.csv', index=False)

# -------------------------------
# 2) Posts table
# -------------------------------
n_posts = 100
# Ensure every influencer has at least one post
post_inf = list(inf_ids) + list(np.random.choice(inf_ids, n_posts - len(inf_ids)))

start_date = datetime.today() - timedelta(days=90)
dates = [start_date + timedelta(days=int(x)) for x in np.random.uniform(0, 90, len(post_inf))]

posts = pd.DataFrame({
    'post_id': range(1, len(post_inf) + 1),
    'influencer_id': post_inf,
    'platform': [influencers.loc[influencers['id'] == iid, 'platform'].values[0] for iid in post_inf],
    'date': dates,
    'url': [f'https://post/{i}' for i in range(1, len(post_inf) + 1)],
    'caption': ['Sample caption'] * len(post_inf),
})

# Engagement metrics — vary by platform
platform_reach_factor = {'Instagram': 0.4, 'YouTube': 0.6, 'Twitter': 0.2}
platform_like_factor = {'Instagram': 0.08, 'YouTube': 0.06, 'Twitter': 0.04}
platform_comment_factor = {'Instagram': 0.015, 'YouTube': 0.01, 'Twitter': 0.008}

posts = posts.merge(influencers[['id', 'follower_count']], left_on='influencer_id', right_on='id')
posts['reach'] = posts.apply(lambda r: int(r['follower_count'] * np.random.uniform(0.3, 0.7) * platform_reach_factor[r['platform']]), axis=1)
posts['likes'] = (posts['reach'] * posts['platform'].map(platform_like_factor) * np.random.uniform(0.8, 1.2, len(posts))).astype(int)
posts['comments'] = (posts['reach'] * posts['platform'].map(platform_comment_factor) * np.random.uniform(0.8, 1.2, len(posts))).astype(int)

# Engagement rate
posts['engagement_rate'] = (posts['likes'] + posts['comments']) / posts['reach']
posts.drop(columns=['id', 'follower_count'], inplace=True)

posts.to_csv('data/posts.csv', index=False)

# -------------------------------
# 3) Tracking table
# -------------------------------
n_users = 2000
users = np.arange(1, n_users + 1)

rows = []
for _ in range(3000):
    user = np.random.choice(users)
    src = np.random.choice(['influencer', 'organic', 'paid_ad'], p=[0.3, 0.5, 0.2])
    inf_id = np.random.choice(inf_ids) if src == 'influencer' else np.nan
    product = np.random.choice(['Protein', 'Multivitamin', 'Snack', 'Supplement'])
    date = start_date + timedelta(days=int(np.random.uniform(0, 90)))

    order_prob = 0.05 if src == 'influencer' else (0.06 if src == 'paid_ad' else 0.015)
    order_flag = np.random.binomial(1, order_prob)
    revenue = order_flag * np.random.choice([499, 999, 1499, 1999])

    campaign = f"camp_{np.random.randint(1, 6)}" if src != 'organic' else None

    rows.append((src, campaign, inf_id, user, product, date, order_flag, revenue))

tracking = pd.DataFrame(rows, columns=['source', 'campaign', 'influencer_id', 'user_id', 'product', 'date', 'orders', 'revenue'])
tracking['influencer_id'] = tracking['influencer_id'].astype('Int64')

tracking.to_csv('data/tracking.csv', index=False)

# -------------------------------
# 4) Payouts table
# -------------------------------
payouts = []
for _, r in influencers.iterrows():
    basis = np.random.choice(['post', 'order'], p=[0.6, 0.4])
    if basis == 'post':
        rate = np.random.randint(2000, 20000)
        num_posts = posts[posts['influencer_id'] == r['id']].shape[0]
        total = rate * num_posts
        orders_count = num_posts
    else:
        rate = np.random.randint(50, 1000)
        orders_count = tracking[(tracking['influencer_id'] == r['id']) & (tracking['source'] == 'influencer')]['orders'].sum()
        total = rate * orders_count

    payouts.append((r['id'], basis, rate, orders_count, total))

payouts_df = pd.DataFrame(payouts, columns=['influencer_id', 'basis', 'rate', 'orders', 'total_payout'])
payouts_df.to_csv('data/payouts.csv', index=False)

print("✅ Data generated in 'data/' folder with engagement_rate and realistic variation")
