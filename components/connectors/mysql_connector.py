import mysql.connector
import pandas as pd
from entities.config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, GAV_MAPPINGS

class MySQLConnector:
    def __init__(self):
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish connection to the database"""
        self.conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        self.cursor = self.conn.cursor()
        print("[INFO] Connected to the database.")

    def disconnect(self):
        """Close the database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("[INFO] Disconnected from the database.")

    def get_schema(self, table_name='jobs'):
        """Retrieve the schema of a table"""
        if not self.conn:
            raise Exception("Connection not established.")
        
        query = f"DESCRIBE {table_name};"
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        schema = {column[0]: column[1] for column in result}
        return schema

    def match_schema_with_gav(self, table_name='jobs', source_file='Linkedin_source'):
        """Compare table schema with GAV mapping"""
        schema = self.get_schema(table_name)
        source_mapping = GAV_MAPPINGS.get(source_file, {})

        all_matched = True
        for global_attr, source_col in source_mapping.items():
            if source_col and source_col not in schema:
                print(f"[WARN] Mismatch: '{source_col}' not found in '{table_name}' table.")
                all_matched = False
        if all_matched:
            print("[INFO] Table schema matches the GAV mapping.")
        return all_matched

    def execute_query(self, query):
        """Run a SQL query and return rows"""
        if not self.conn:
            raise Exception("Connection not established.")
        
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def fetch_data_as_dataframe(self, query):
        """Run a SQL query and return result as DataFrame"""
        if not self.conn:
            raise Exception("Connection not established.")
        
        return pd.read_sql(query, self.conn)

    def fetch_query(self, query):
        """Alias for execute_query for compatibility with pipeline"""
        return self.execute_query(query)