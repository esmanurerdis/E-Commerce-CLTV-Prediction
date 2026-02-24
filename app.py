import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ==============================================================================
# 1. SAYFA YAPILANDIRMASI VE DİNAMİK YOLLAR
# ==============================================================================
st.set_page_config(
    page_title="E-Commerce RFM & CLTV Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- TASARIM GÜNCELLEME ---
st.markdown("""
    <style>
    .stApp { background-color: white !important; }
    [data-testid="stSidebar"] { background-color: #084D6B !important; }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: white !important; }
    div[data-baseweb="select"] > div { color: #084D6B !important; background-color: white !important; border-radius: 5px !important; }
    [data-testid="stMetric"] { background-color: #084D6B !important; padding: 20px !important; border-radius: 15px !important; }
    [data-testid="stMetricLabel"] { color: #d1d1d1 !important; font-weight: bold !important; }
    [data-testid="stMetricValue"] { color: white !important; }
    div.stButton > button { background-color: #084D6B !important; color: white !important; border-radius: 10px !important; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# Streamlit Cloud ve Yerel çalışma için en sağlam dosya yolu yöntemi
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==============================================================================
# 2. VERİ YÜKLEME FONKSİYONLARI
# ==============================================================================
@st.cache_data
def load_data():
    # Dosya isimlerini GitHub'daki halleriyle birebir eşleştirin
    rfm_file = os.path.join(BASE_DIR, 'rfm_results.csv')
    cltv_file = os.path.join(BASE_DIR, 'cltv_results.csv')
    
    # Hata ayıklama için dosyaları kontrol et
    if not os.path.exists(rfm_file):
        st.error(f"Kritik Hata: rfm_results.csv bulunamadı! Yol: {rfm_file}")
        return None
    
    try:
        rfm = pd.read_csv(rfm_file)
        
        # Eğer cltv_results.csv yoksa uygulamayı kırmayalım, sadece RFM ile devam edelim
        if os.path.exists(cltv_file):
            cltv = pd.read_csv(cltv_file)
            full_df = rfm.merge(cltv[['customer_id', 'clv_6months', 'predicted_purchases_6m']], 
                              on='customer_id', how='left')
        else:
            st.warning("Not: cltv_results.csv bulunamadı, sadece RFM verileri gösteriliyor.")
            full_df = rfm
            # Eksik kolonları hata vermemesi için boş dolduruyoruz
            if 'clv_6months' not in full_df.columns:
                full_df['clv_6months'] = 0
            if 'predicted_purchases_6m' not in full_df.columns:
                full_df['predicted_purchases_6m'] = 0
                
        return full_df
    except Exception as e:
        st.error(f"Veri işleme hatası: {e}")
        return None

df = load_data()

# ==============================================================================
# 3. SIDEBAR VE NAVİGASYON
# ==============================================================================
st.sidebar.title("🎯 Analiz Paneli")
st.sidebar.markdown("---")

if df is not None:
    view_option = st.sidebar.radio(
        "Görünüm Seçin:",
        ["🏠 Genel Bakış", "📈 RFM Segmentasyonu", "💎 CLTV Tahminleri", "👥 Müşteri Detayı"]
    )
    st.sidebar.markdown("---")
    st.sidebar.info(f"**Veri Güncelliği:** {datetime.now().strftime('%d-%m-%Y')}")
else:
    st.error("⚠️ Analiz dosyaları bulunamadı! Lütfen GitHub deponuzda rfm_results.csv dosyasının olduğundan emin olun.")
    st.stop()

# ==============================================================================
# 4. DASHBOARD GÖRÜNÜMLERİ
# ==============================================================================

if view_option == "🏠 Genel Bakış":
    st.title("📊 E-Commerce Genel Durum")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Toplam Müşteri", f"{len(df):,}")
    with col2:
        st.metric("Toplam Tahmini Gelir (6 Ay)", f"₺{df['clv_6months'].sum():,.0f}")
    with col3:
        st.metric("Ortalama Müşteri Değeri", f"₺{df['clv_6months'].mean():.2f}")
    with col4:
        st.metric("Şampiyon Müşteriler", len(df[df['Segment'] == 'Champions']) if 'Segment' in df.columns else 0)

    st.markdown("---")
    
    c1, c2 = st.columns(2)
    if 'Segment' in df.columns:
        with c1:
            st.subheader("Segment Dağılımı")
            fig = px.pie(df, names='Segment', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            st.subheader("Segment Bazlı Ortalama CLTV")
            seg_avg = df.groupby('Segment')['clv_6months'].mean().sort_values()
            fig = px.bar(x=seg_avg.values, y=seg_avg.index, orientation='h',
                         labels={'x': 'Ort. CLTV', 'y': 'Segment'},
                         color=seg_avg.index, color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig, use_container_width=True)

elif view_option == "📈 RFM Segmentasyonu":
    st.header("RFM (Recency, Frequency, Monetary) Analizi")
    fig = px.scatter(df, x="Recency", y="Frequency", color="Segment" if "Segment" in df.columns else None,
                     size="Monetary", hover_data=['customer_id'],
                     title="RFM Dağılım Matrisi (Boyut = Monetary)",
                     color_discrete_sequence=px.colors.qualitative.Vivid)
    st.plotly_chart(fig, use_container_width=True)

elif view_option == "💎 CLTV Tahminleri":
    st.header("6 Aylık CLTV Tahmin Analizi")
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.subheader("En Değerli 20 Müşteri")
        top_20 = df.nlargest(20, 'clv_6months')
        fig = px.bar(top_20, x='clv_6months', y=top_20['customer_id'].astype(str),
                     orientation='h', color='Segment' if 'Segment' in df.columns else None,
                     title="Müşteri Bazlı CLTV Beklentisi")
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        st.subheader("Uyuyan Devler 💎")
        if 'Segment' in df.columns:
            giants = df[df['Segment'] == 'At Risk'].nlargest(10, 'clv_6months')
            st.table(giants[['customer_id', 'clv_6months']].rename(columns={'clv_6months': 'Potansiyel ₺'}))

elif view_option == "👥 Müşteri Detayı":
    st.header("Müşteri Özel Analiz Kartı")
    search_id = st.selectbox("Müşteri ID seçin:", sorted(df['customer_id'].unique()))
    if search_id:
        user_data = df[df['customer_id'] == search_id].iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Segment", user_data.get('Segment', 'N/A'))
        c2.metric("Son Alışveriş", f"{int(user_data['Recency'])} gün önce")
        c3.metric("Alışveriş Sıklığı", f"{int(user_data['Frequency'])} kez")
        c4.metric("Gelecek Tahmini (6ay)", f"{user_data.get('predicted_purchases_6m', 0):.1f} sipariş")

st.sidebar.markdown("---")
st.sidebar.write("Developed by Esmanur Erdiş")