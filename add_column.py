# add_column.py
import sqlite3
import os

# ডেটাবেস ফাইলের পাথ
db_path = os.path.join(os.path.dirname(__file__), 'bot_database.db')

try:
    # SQLite সংযোগ তৈরি করুন
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # কলাম যোগ করার চেষ্টা করুন
    cursor.execute("ALTER TABLE transactions ADD COLUMN txid VARCHAR(500)")
    conn.commit()
    
    print("✅ Column 'txid' added successfully!")
    
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("✅ Column 'txid' already exists!")
    else:
        print(f"⚠️ Error: {e}")
finally:
    conn.close()