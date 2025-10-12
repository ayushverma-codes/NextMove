from typing import Dict, Optional
from components.validator.SQLValidator import SQLValidator
from entities.config import GLOBAL_SCHEMA, GAV_MAPPINGS, SOURCE_TO_TABLE, SOURCE_TO_DB_Type


class FederatedSQLValidator:
    """
    Wrapper around SQLValidator to support multiple sources (MySQL/Postgres)
    and semantic validation using GAV mappings and global schema.
    """

    def __init__(self):
        # Create validator instances for MySQL and Postgres
        self.validators = {
            "MySQL": SQLValidator(dialect="mysql"),
            "PostgreSQL": SQLValidator(dialect="postgres")
        }

    def get_source_schema(self, source_name: str) -> Dict[str, list]:
        """
        Generate a table->columns schema dictionary for SQLValidator from GAV mappings.
        """
        schema = {}
        if source_name in GAV_MAPPINGS and source_name in SOURCE_TO_TABLE:
            table_name = SOURCE_TO_TABLE[source_name]
            columns_mapping = GAV_MAPPINGS[source_name]
            # Only include columns that exist in source
            columns = [col for col in columns_mapping.values() if col]
            schema[table_name] = columns
        return schema

    def validate_query(self, query: str, source_name: Optional[str] = None) -> Dict:
        """
        Validate a query for a specific source.
        If source_name is None, uses GLOBAL_SCHEMA.
        """
        # Determine SQL dialect
        dialect = "mysql"  # default
        if source_name and source_name in SOURCE_TO_DB_Type:
            db_type = SOURCE_TO_DB_Type[source_name]
            dialect = "mysql" if db_type.lower() == "mysql" else "postgres"

        # Pick validator instance
        validator = self.validators["MySQL"] if dialect == "mysql" else self.validators["PostgreSQL"]

        # Determine schema
        schema = self.get_source_schema(source_name) if source_name else { "global": list(GLOBAL_SCHEMA.keys()) }

        # Update validator schema
        validator.schema = schema

        # Validate query
        result = validator.validate(query)
        return result

