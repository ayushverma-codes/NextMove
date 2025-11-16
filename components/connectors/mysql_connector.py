# D:\Projects\NextMove\components\connectors\mysql_connector.py

import mysql.connector
from mysql.connector import Error
from typing import List, Dict, Any

class MySQLConnector:
    """
    A MySQL connector class that supports connecting to
    specific databases with provided credentials and a timeout.
    """
    def __init__(self, host, user, password, database, timeout=5):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = 3306
        self.timeout = timeout  # Connection timeout
        self.connection = None
        self.cursor = None

    def connect(self):
        """Establishes the database connection with a timeout."""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                connection_timeout=self.timeout # Fail fast if DB is down
            )
            if self.connection.is_connected():
                self.cursor = self.connection.cursor()
        except Error as e:
            print(f"[ERROR] Could not connect to {self.database}: {e}")
            raise e

    def disconnect(self):
        """Closes the database connection."""
        if self.connection and self.connection.is_connected():
            self.cursor.close()
            self.connection.close()

    def execute_query_as_dict(self, query: str) -> List[Dict[str, Any]]:
        """
        Executes a query and returns the results as a list of dictionaries.
        This is essential for JSON serialization and for the LLM.
        """
        if not self.connection or not self.cursor:
            print("[ERROR] Not connected. Call connect() first.")
            return []
            
        try:
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            # Get column names from cursor description
            columns = [col[0] for col in self.cursor.description]
            
            # Convert list of tuples to list of dicts
            result_list = [dict(zip(columns, row)) for row in rows]
            return result_list
            
        except Error as e:
            print(f"[ERROR] Query failed: {e}\nQuery: {query}")
            # Raise the exception so the pipeline can catch it
            raise e

    def execute_query(self, query: str):
        """Executes a query and returns raw tuples."""
        if not self.connection or not self.cursor:
            print("[ERROR] Not connected. Call connect() first.")
            return []
        
        try:
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            return rows
        except Error as e:
            print(f"[ERROR] Query failed: {e}\nQuery: {query}")
            raise e