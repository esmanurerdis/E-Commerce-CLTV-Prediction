import os
import pandas as pd
import sqlite3
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import summary_data_from_transaction_data
import warnings

warnings.filterwarnings('ignore')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'ecommerce.db')
rfm_results_path = os.path.join(BASE_DIR, 'rfm_results.csv')
cltv_output_path = os.path.join(BASE_DIR, 'cltv_results.csv')

conn = sqlite3.connect(db_path)
query = "SELECT customer_id, order_date, total_amount FROM orders WHERE total_amount > 0"
transactions = pd.read_sql_query(query, conn)
transactions['order_date'] = pd.to_datetime(transactions['order_date'])

# BG/NBD Hazırlık
summary = summary_data_from_transaction_data(
    transactions, 'customer_id', 'order_date', 'total_amount',
    observation_period_end=transactions['order_date'].max()
)

bgf = BetaGeoFitter(penalizer_coef=0.001)
bgf.fit(summary['frequency'], summary['recency'], summary['T'])

# 1. DÜZELTME: 180 GÜN (6 AY) TAHMİNİ
future_purchases = bgf.conditional_expected_number_of_purchases_up_to_time(
    180, summary['frequency'], summary['recency'], summary['T']
)

# Gamma-Gamma
ggf = GammaGammaFitter(penalizer_coef=0.01)
summary_gg = summary[(summary['frequency'] > 0) & (summary['monetary_value'] > 0)]
ggf.fit(summary_gg['frequency'], summary_gg['monetary_value'])

# 2. DÜZELTME: 6 AYLIK CLTV (GÜNLÜK VERİ freq='D')
predicted_clv = ggf.customer_lifetime_value(
    bgf, summary['frequency'], summary['recency'], summary['T'], summary['monetary_value'],
    time=6, freq='D', discount_rate=0.01
)

# HATALI KISIM BURASIYDI - DÜZELTİLDİ:
cltv_df = pd.DataFrame({
    'predicted_purchases_6m': future_purchases,
    'clv_6months': predicted_clv
}).reset_index() # index olan customer_id'yi burada sütun yapıyoruz

# 3. DÜZELTME: HATA KORUMALI MERGE
if os.path.exists(rfm_results_path):
    rfm = pd.read_csv(rfm_results_path)
    # rfm içindeki country veya Country farketmeksizin kontrol edelim
    available_cols = [c for c in ['customer_id', 'Segment', 'country', 'Country'] if c in rfm.columns]
    cltv_df = cltv_df.merge(rfm[available_cols], on='customer_id', how='left')

cltv_df.to_csv(cltv_output_path, index=False, encoding='utf-8-sig')
conn.close()
print("\n" + "="*50)
print("✅ CLTV TAMAMLANDI - Tahminler artık gerçekçi seviyede!")
print("="*50)