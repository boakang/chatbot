from database import DatabaseHelper

print("Testing database connection to Iowa Liquor Sales 2022...")
db = DatabaseHelper()
print(f"Connection String being used: {db.connection_string}")
print("-" * 50)

try:
    conn = db.get_connection()
    print("✅ Connection successful!")
    
    cursor = conn.cursor()
    # Test 1: Count records in the table
    cursor.execute("SELECT COUNT(*) FROM dbo.Iowa_Liquor_Sales2022")
    count = cursor.fetchone()[0]
    print(f"✅ Found {count:,} sales records in dbo.Iowa_Liquor_Sales2022")
    
    # Test 2: Peek at the first 3 records
    print("\n🔍 First 3 records:")
    cursor.execute("SELECT TOP 3 store_name, city, sale_dollars FROM dbo.Iowa_Liquor_Sales2022")
    for row in cursor.fetchall():
        print(f" - Store: {row[0]}, City: {row[1]}, Sale: ${row[2]:,.2f}")
    
    conn.close()
    print("\n✅ Database is ready and structure is verified!")
    
except Exception as e:
    print(f"❌ Verification failed: {e}")
    print("\n💡 TIP: Make sure your credentials in config.py or .env are correct.")