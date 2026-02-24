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
                cursor.execute(f"SELECT `Job Title`, Company, location, skills, `Salary Range`, `Work Type` FROM `job_listings` WHERE location LIKE '%Remote%' AND `Job Title` LIKE '%data science%' AND `Salary Range` >= 120000 AND `Job Description` LIKE '%stock options%' AND `Job Description` LIKE '%flexible hours%' LIMIT 10")
                table_exists = cursor.fetchone()
                if table_exists:
                    print("📋 Table 'job_listings' exists in the database.")
                else:
                    # print("ℹ Table 'job_listings' does NOT exist in the database.")
                    pass

                # Execute a test query: get first 5 rows
                cursor.execute("SELECT * FROM job_listings LIMIT 5;")
                rows = cursor.fetchall()
                if rows:
                    print("📝 Sample rows from 'job_listings':")
                    for row in rows:
                        print(row)
                else:
                    print("ℹ No data found in 'job_listings' yet.")

            cursor.close()

    except Error as e:
        print(f"❌ Connection failed or query error: {e}")

    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()
            print("🔒 MySQL connection closed.")


# 🔧 Update your MySQL credentials here
test_mysql_connection(
    host="192.168.41.129",        # MySQL server IP
    user="ayush_73",              # MySQL username
    password="HashMap@123",       # MySQL password
    database="naukri_source"      # Database to check
)