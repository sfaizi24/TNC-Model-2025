import sqlite3

conn = sqlite3.connect('backend/data/databases/odds.db')
cursor = conn.cursor()

print("=== Schema ===")
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='betting_odds_highest_scorer'")
print(cursor.fetchone()[0])

print("\n=== Sample Data ===")
cursor.execute('SELECT * FROM betting_odds_highest_scorer LIMIT 10')
columns = [desc[0] for desc in cursor.description]
print("Columns:", columns)

for row in cursor.fetchall():
    print(row)

conn.close()
