import pandas as pd
import sqlite3
import os
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'ecommerce.db')
rfm_output_path = os.path.join(BASE_DIR, 'rfm_results.csv')

print("="*60)
print("RFM ANALİZİ BAŞLANIYOR")
print("="*60)

conn = sqlite3.connect(db_path)
query = """
SELECT 
    o.customer_id,
    o.order_date,
    SUM(o.total_amount) as order_amount,
    c.country
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
GROUP BY o.customer_id, o.order_date, c.country
"""
df = pd.read_sql_query(query, conn)
df['order_date'] = pd.to_datetime(df['order_date'])

reference_date = df['order_date'].max() + pd.Timedelta(days=1)
rfm = df.groupby(['customer_id', 'country']).agg({
    'order_date': lambda date: (reference_date - date.max()).days,
    'customer_id': 'count',
    'order_amount': 'sum'
})

rfm.columns = ['Recency', 'Frequency', 'Monetary']
rfm = rfm.reset_index()

rfm['R_Score'] = pd.qcut(rfm['Recency'], q=4, labels=[4, 3, 2, 1], duplicates='drop')
rfm['F_Score'] = pd.qcut(rfm['Frequency'].rank(method='first'), q=4, labels=[1, 2, 3, 4])
rfm['M_Score'] = pd.qcut(rfm['Monetary'], q=4, labels=[1, 2, 3, 4])
rfm['RFM_Score'] = rfm['R_Score'].astype(str) + rfm['F_Score'].astype(str) + rfm['M_Score'].astype(str)

def get_segment(score_str):
    if score_str.startswith('44'): return 'Champions'
    elif int(score_str[0]) >= 3 and int(score_str[1]) >= 3: return 'Loyal Customers'
    elif int(score_str[0]) <= 2 and int(score_str[1]) >= 3: return 'At Risk'
    elif int(score_str[0]) <= 2 and int(score_str[1]) <= 2: return 'Lost'
    else: return 'Potential'

rfm['Segment'] = rfm['RFM_Score'].apply(get_segment)
rfm.to_csv(rfm_output_path, index=False, encoding='utf-8-sig')
conn.close()
print("✅ RFM TAMAMLANDI - Country sütunu eklendi.")