import os
os.environ['VERCEL'] = '1'
import sqlite3

# Check which columns are missing
conn = sqlite3.connect('bookhub.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(books)")
columns = {row[1] for row in cursor.fetchall()}
print("Books table columns:", sorted(columns))
print("\nMissing columns:")
for col in ['is_visible', 'is_out_of_stock', 'rejection_reason', 'rejected_at', 'rejected_by']:
    status = '✅' if col in columns else '❌'
    print(f"  {col}: {status}")
