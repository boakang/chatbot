import pyodbc

server = "schema-sql.database.windows.net"
database = "tickets"
username = "thbao"
password = "AnhiuTH@1307"

connection_string = (
    f"Driver={{ODBC Driver 18 for SQL Server}};"
    f"Server=tcp:{server},1433;"
    f"Database={database};"
    f"Uid={username};"
    f"Pwd={password};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=yes;"
    f"Connection Timeout=60;"
)

print("Testing database connection...")
print(f"Server: {server}")
print(f"Database: {database}")
print("-" * 50)

try:
    conn = pyodbc.connect(connection_string)
    print("✅ Connection successful!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM AdminKeys")
    count = cursor.fetchone()[0]
    print(f"✅ Found {count} admin keys in database")
    
    conn.close()
    print("✅ Database ready!")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")