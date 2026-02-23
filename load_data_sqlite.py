import pandas as pd
import sqlite3
import warnings

warnings.filterwarnings('ignore')

# ===== SQLite Bağlantı =====
db_path = r'C:\Users\esman\OneDrive\Belgeler\Projeler\E-Commerce RFM & CLTV Analysis\ecommerce.db'

print("SQLite veritabanı oluşturuluyor...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
print(f"✓ Veritabanı: {db_path}")

# ===== XLSX Dosyasını Oku =====
print("\nXLSX dosyası okunuyor...")
xlsx_path = r'C:\Users\esman\OneDrive\Belgeler\Projeler\E-Commerce RFM & CLTV Analysis\online_retail_II.xlsx'

try:
    xls = pd.ExcelFile(xlsx_path)
    print(f"✓ Sheet'ler bulundu: {xls.sheet_names}")
    
    df = pd.read_excel(xlsx_path, sheet_name=0)
    print(f"✓ Dosya başarıyla okundu. Satır sayısı: {len(df)}")
except Exception as e:
    print(f"✗ Dosya okunurken hata: {e}")
    exit()

# ===== Verileri Temizle =====
print("\nVeriler temizleniyor...")

df = df.dropna(subset=['Invoice', 'Customer ID'])
df = df[df['Quantity'] > 0]
df = df[df['Price'] > 0]

df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'], format='%d/%m/%Y %H:%M', errors='coerce')
df['Customer ID'] = df['Customer ID'].astype(int)

print(f"✓ Temizleme tamamlandı. Kalan satır: {len(df)}")

# ===== Tablolar Oluştur =====
print("\nTablolar oluşturuluyor...")

cursor.execute('''
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    country TEXT,
    first_purchase_date DATETIME
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_id INTEGER,
    order_date DATETIME,
    total_amount REAL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT,
    product_code TEXT,
    product_description TEXT,
    quantity INTEGER,
    unit_price REAL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
)
''')

conn.commit()
print("✓ Tablolar oluşturuldu")

# ===== Customers Yükle =====
print("\nMüşteriler yükleniyor...")
customers = df[['Customer ID', 'Country']].drop_duplicates('Customer ID').copy()
customers['first_purchase_date'] = customers['Customer ID'].map(
    df.groupby('Customer ID')['InvoiceDate'].min()
)
customers = customers.rename(columns={'Customer ID': 'customer_id', 'Country': 'country'})

customers.to_sql('customers', conn, if_exists='append', index=False)
print(f"✓ {len(customers)} müşteri yüklendi")

# ===== Orders Yükle =====
print("Siparişler yükleniyor...")
orders = df[['Invoice', 'Customer ID', 'InvoiceDate']].drop_duplicates('Invoice').copy()
order_totals = df.groupby('Invoice').apply(lambda x: (x['Quantity'] * x['Price']).sum()).reset_index(name='total_amount')
orders = orders.merge(order_totals, left_on='Invoice', right_on='Invoice')
orders = orders.rename(columns={'Invoice': 'order_id', 'Customer ID': 'customer_id', 'InvoiceDate': 'order_date'})

orders.to_sql('orders', conn, if_exists='append', index=False)
print(f"✓ {len(orders)} sipariş yüklendi")

# ===== Order Items Yükle =====
print("Sipariş detayları yükleniyor...")
order_items = df[['Invoice', 'StockCode', 'Description', 'Quantity', 'Price']].copy()
order_items = order_items.rename(columns={
    'Invoice': 'order_id',
    'StockCode': 'product_code',
    'Description': 'product_description',
    'Quantity': 'quantity',
    'Price': 'unit_price'
})

# Batch yükleme
batch_size = 5000
for i in range(0, len(order_items), batch_size):
    batch = order_items.iloc[i:i+batch_size]
    batch.to_sql('order_items', conn, if_exists='append', index=False)
    print(f"  {min(i+batch_size, len(order_items))}/{len(order_items)} yüklendi...")

print(f"✓ {len(order_items)} sipariş detayı yüklendi")

# ===== Sonuç =====
print("\n" + "="*50)
print("✓ TÜMÜ BAŞARILI!")
print("="*50)

cursor.execute("SELECT COUNT(*) FROM customers")
customer_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM orders")
order_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM order_items")
item_count = cursor.fetchone()[0]

print(f"\n📊 Veritabanı İstatistikleri:")
print(f"   Müşteri: {customer_count}")
print(f"   Sipariş: {order_count}")
print(f"   Sipariş Detayı: {item_count}")

conn.close()
print("\n✓ Bağlantı kapatıldı.")
print(f"✓ Veritabanı dosyası: {db_path}")