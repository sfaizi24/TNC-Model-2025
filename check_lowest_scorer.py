import sqlite3

conn = sqlite3.connect('backend/data/databases/odds.db')
cursor = conn.cursor()

# Check if table exists
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='betting_odds_lowest_scorer'")
result = cursor.fetchone()

if result:
    print("=== Schema ===")
    print(result[0])
    
    print("\n=== Sample Data ===")
    cursor.execute('SELECT * FROM betting_odds_lowest_scorer LIMIT 10')
    columns = [desc[0] for desc in cursor.description]
    print("Columns:", columns)
    
    for row in cursor.fetchall():
        print(row)
else:
    print("Table 'betting_odds_lowest_scorer' not found")

conn.close()
