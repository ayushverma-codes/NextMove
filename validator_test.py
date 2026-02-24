# D:\Projects\NextMove\tests\validator_tester.py

import csv
import re
from typing import Dict
from components.validator.SQLValidatorWrapper import FederatedSQLValidator
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score

# -----------------------------
# Helper: Parse CREATE TABLE SQL to dict
# -----------------------------
def parse_schema(sql_schema: str) -> Dict[str, list]:
    """
    Extracts table names and columns from CREATE TABLE statements.
    Returns: {table_name: [col1, col2, ...]}
    """
    schema_dict = {}
    # Split multiple CREATE TABLE statements
    statements = re.findall(r'CREATE TABLE\s+(\w+)\s*\((.*?)\);', sql_schema, re.IGNORECASE | re.DOTALL)
    for table_name, cols_str in statements:
        # Extract column names ignoring types and constraints
        cols = []
        for line in cols_str.split(','):
            line = line.strip()
            if not line:
                continue
            col_name = line.split()[0]  # first token is column name
            cols.append(col_name)
        schema_dict[table_name] = cols
    return schema_dict

# -----------------------------
# Run Validator on CSV
# -----------------------------
def test_queries_from_csv(csv_path: str):
    validator = FederatedSQLValidator()
    y_true = []
    y_pred = []

    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = row['SQL_QUERIES'].strip()
            expected_status = row['STATUS'].strip().upper()
            sql_schema = row['SCHEMAS']

            # Build table->columns schema
            schema_dict = parse_schema(sql_schema)

            # Assign schema to validator (single source)
            validator_schema_backup = validator.validators["MySQL"].schema.copy()
            validator.validators["MySQL"].schema = schema_dict

            # Validate query
            result = validator.validators["MySQL"].validate(query)
            predicted_status = "VALID" if result['is_valid'] else "INVALID"

            y_true.append(expected_status)
            y_pred.append(predicted_status)

            # Restore old schema
            validator.validators["MySQL"].schema = validator_schema_backup

            print(f"Query: {query}\nExpected: {expected_status}, Predicted: {predicted_status}\n")

    # Metrics
    print("\n=== Confusion Matrix ===")
    print(confusion_matrix(y_true, y_pred, labels=["INVALID", "VALID"]))

    print("\n=== Classification Report ===")
    print(classification_report(y_true, y_pred, labels=["INVALID", "VALID"]))

    print("\n=== Accuracy ===")
    print(f"{accuracy_score(y_true, y_pred):.2f}")

# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":
    csv_file = r"D:\Projects\NextMove\workspace_folder\input\SQLQueryValidatorTest.csv"
    test_queries_from_csv(csv_file)
