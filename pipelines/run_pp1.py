from components.connectors.mysql_connector import MySQLConnector

def run_pipeline():
    mysql_connector = MySQLConnector()

    try:
        # Step 1: Connect to DB
        mysql_connector.connect()

        # Step 2: Match schema
        table_name = 'jobs'
        source_file = 'LinkedIn_Job_Postings.csv'

        print(f"[INFO] Validating schema for table: {table_name} using source mapping: {source_file}")
        matched = mysql_connector.match_schema_with_gav(table_name=table_name, source_file=source_file)

        if not matched:
            print("[ERROR] Schema mismatch. Pipeline stopped.")
            return

        # Step 3: Run a query
        query = f"SELECT * FROM {table_name} LIMIT 10;"
        print("[INFO] Executing query:", query)
        rows = mysql_connector.execute_query(query)
        for row in rows:
            print(row)

        # Step 4: Optional - Pandas DataFrame
        # df = mysql_connector.fetch_data_as_dataframe(query)
        # print("\n[INFO] Data as DataFrame:")
        # print(df.head())

    except Exception as e:
        print(f"[EXCEPTION] {str(e)}")

    finally:
        # Step 5: Disconnect
        # mysql_connector.disconnect()
        pass
