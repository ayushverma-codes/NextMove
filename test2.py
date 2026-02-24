import mysql.connector
from mysql.connector import Error


def test_mysql_connection(host, user, password, database=None):
    try:
        # Connect to MySQL server
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=3306
        )

        if connection.is_connected():
            print(f"✅ Connected successfully to MySQL server at '{host}'")

            cursor = connection.cursor()

            # If no database specified, show databases
            if not database:
                cursor.execute("SHOW DATABASES;")
                databases = cursor.fetchall()
                print("Databases on the server:")
                for db in databases:
                    print("   -", db[0])
            else:
                # Check if table exists
                cursor.execute(f"SHOW TABLES LIKE 'jobs';")
                table_exists = cursor.fetchone()
                if table_exists:
                    print("📋 Table 'jobs' exists in the database.")
                else:
                    print("ℹ Table 'jobs' does NOT exist in the database.")

                # Execute a test query: get first 5 rows
                cursor.execute("SELECT * FROM jobs LIMIT 5;")
                rows = cursor.fetchall()
                if rows:
                    print("📝 Sample rows from 'jobs':")
                    for row in rows:
                        print(row)
                else:
                    print("ℹ No data found in 'jobs' yet.")

            cursor.close()

    except Error as e:
        print(f"❌ Connection failed or query error: {e}")

    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()
            print("🔒 MySQL connection closed.")


# 🔧 Update your MySQL credentials here
test_mysql_connection(
    host="192.168.41.131",        # MySQL server IP
    user="source_server1",              # MySQL username
    password="24025",       # MySQL password
    database="linkedin_source"      # Database to check
)