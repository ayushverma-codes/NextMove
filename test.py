import mysql.connector
from mysql.connector import Error

def test_mysql_connection(host, user, password, database=None):
    try:
        # Attempt connection
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,   # Optional, you can leave it None to connect to server only
            port=3306
        )

        # Check connection status
        if connection.is_connected():
            print(f"✅ Connected successfully to MySQL server at '{host}'")
            
            # Get server info
            server_info = connection.get_server_info()
            print("Server version:", server_info)

            cursor = connection.cursor()

            # ✅ Execute a test query
            if database:
                cursor.execute("SHOW TABLES;")
                tables = cursor.fetchall()
                if tables:
                    print("📋 Tables in the database:")
                    for table in tables:
                        print("   -", table[0])
                else:
                    print("ℹ  No tables found in the database yet.")
            else:
                cursor.execute("SHOW DATABASES;")
                databases = cursor.fetchall()
                print("📚 Databases on the server:")
                for db in databases:
                    print("   -", db[0])

            # ✅ Optional: run any custom SQL command
            # cursor.execute("SELECT * FROM job_listings LIMIT 5;")
            # print(cursor.fetchall())

            cursor.close()

    except Error as e:
        print(f"❌ Connection failed or query error: {e}")

    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()
            print("🔒 MySQL connection closed.")


# 🔧 Update your MySQL credentials here
test_mysql_connection(
    host="192.168.41.129",        # your MySQL host machine's IP
    user="ayush_73",        # your MySQL username
    password="HashMap@123",  # your password
    database="naukri_source"    # optional: specify database name or set None
)