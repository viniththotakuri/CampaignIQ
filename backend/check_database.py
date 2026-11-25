"""
CampaignIQ Database Audit Script
Prints table names and record counts from backend/campaigniq.db
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "campaigniq.db"

if not DB_PATH.exists():
    print(f"Database file not found at: {DB_PATH}")
    exit(1)

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    AND name NOT LIKE 'sqlite_%'
    ORDER BY name
""")

tables = cursor.fetchall()

print("\n========== CAMPAIGNIQ DATABASE AUDIT ==========\n")
print(f"Database File: {DB_PATH}\n")

for table in tables:
    table_name = table[0]
    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
    count = cursor.fetchone()[0]
    print(f"Table: {table_name:<15} | Records: {count}")

print("\n" + "=" * 47 + "\n")
connection.close()
