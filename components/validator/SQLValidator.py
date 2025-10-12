import sqlglot
from sqlglot import parse_one, transpile, exp
from sqlglot.errors import ParseError, TokenError, UnsupportedError
from typing import Dict, List, Optional

class SQLValidator:
    DIALECTS = ['postgres', 'mysql']

    def __init__(self, dialect: str = 'postgres', schema: Optional[Dict[str, List[str]]] = None):
        self.dialect = dialect if dialect in self.DIALECTS else 'postgres'
        self.schema = schema or {}

    def validate(self, query: str) -> Dict:
        result = {
            'is_valid': False,
            'message': '',
            'errors': [],
            'warnings': [],
            'query_type': None,
            'parsed_tree': None
        }

        if not query or not query.strip():
            result['errors'].append('Query is empty')
            result['message'] = 'Invalid: Query is empty'
            return result

        try:
            parsed = parse_one(query, read=self.dialect, error_level=None)

            # Early syntax checks before semantic validation
            syntax_errors = self._check_common_syntax(parsed)
            if syntax_errors:
                result['errors'].extend(syntax_errors)
                result['message'] = 'Invalid: Syntax errors'
                return result

            # Check for empty INSERT VALUES
            if isinstance(parsed, sqlglot.exp.Insert):
                if not parsed.expressions or all(e is None for e in parsed.expressions):
                    result['errors'].append("INSERT has empty VALUES list")
                    result['message'] = "Invalid: Empty VALUES in INSERT"
                    return result

            # If we get here, the query is syntactically valid
            result['is_valid'] = True
            result['message'] = 'Query syntax is valid'
            result['query_type'] = type(parsed).__name__
            result['parsed_tree'] = parsed.sql(pretty=True)

            # Warnings for potentially dangerous operations
            result['warnings'] = self._check_warnings(parsed)

            # Semantic validation if schema is provided
            if self.schema:
                sem_errors = self._check_semantics(parsed)
                result['errors'].extend(sem_errors)
                if sem_errors:
                    result['is_valid'] = False
                    result['message'] = 'Invalid: Semantic errors'

        except ParseError as e:
            result['errors'].append(f'Parse error: {str(e)}')
            result['message'] = 'Invalid: Parse error'
        except TokenError as e:
            result['errors'].append(f'Token error: {str(e)}')
            result['message'] = 'Invalid: Token error'
        except UnsupportedError as e:
            result['errors'].append(f'Unsupported syntax: {str(e)}')
            result['message'] = 'Invalid: Unsupported syntax'
        except Exception as e:
            result['errors'].append(f'Unexpected error: {str(e)}')
            result['message'] = 'Invalid: Unexpected error'

        return result

    def _check_common_syntax(self, parsed) -> List[str]:
        """Check for missing FROM in SELECT or target table in UPDATE/DELETE."""
        errors = []

        # SELECT must have FROM
        for select in parsed.find_all(exp.Select):
            if not select.args.get("from"):
                errors.append('SELECT statement missing FROM clause')

        # UPDATE must have target table
        for update in parsed.find_all(exp.Update):
            if not update.this:
                errors.append('UPDATE statement missing target table')

        # DELETE must have FROM clause
        for delete in parsed.find_all(exp.Delete):
            if not delete.args.get('this'):
                errors.append('DELETE statement missing FROM clause')

        return errors

    def _check_warnings(self, parsed) -> List[str]:
        warnings = []

        # UPDATE without WHERE
        for update in parsed.find_all(exp.Update):
            if not update.args.get('where'):
                warnings.append('UPDATE without WHERE clause will modify all rows')

        # DELETE without WHERE
        for delete in parsed.find_all(exp.Delete):
            if not delete.args.get('where'):
                warnings.append('DELETE without WHERE clause will remove all rows')

        # SELECT *
        for select in parsed.find_all(exp.Select):
            if any(select.find_all(exp.Star)):
                warnings.append('SELECT * may have performance implications in production')

        # Empty INSERT VALUES
        for insert in parsed.find_all(exp.Insert):
            values = insert.args.get('expressions')
            if not values or all(not v.args for v in values):
                warnings.append('INSERT has empty VALUES list')

        # Missing semicolon (style)
        if not parsed.sql().rstrip().endswith(';'):
            warnings.append('Query does not end with semicolon (optional but recommended)')

        return list(set(warnings))

    def _check_semantics(self, parsed) -> List[str]:
        errors = []

        # Tables in query
        tables_in_query = [t.name for t in parsed.find_all(exp.Table)]
        for table in tables_in_query:
            if table not in self.schema:
                errors.append(f'Table "{table}" does not exist in schema')

        # Columns in query
        for column in parsed.find_all(exp.Column):
            table_name = column.find(exp.Table)
            col_table = table_name.name if table_name else None
            col_name = column.name
            if col_table:
                if col_table in self.schema and col_name not in self.schema[col_table]:
                    errors.append(f'Column "{col_name}" does not exist in table "{col_table}"')
            else:
                if not any(col_name in self.schema[t] for t in tables_in_query if t in self.schema):
                    errors.append(f'Column "{col_name}" does not exist in any referenced table')

        return errors

    def validate_multiple(self, queries: List[str]) -> List[Dict]:
        return [self.validate(q) for q in queries]

    def transpile(self, query: str, target_dialect: str) -> Dict:
        result = self.validate(query)
        if result['is_valid']:
            try:
                transpiled = transpile(query, read=self.dialect, write=target_dialect)[0]
                result['transpiled'] = transpiled
                result['target_dialect'] = target_dialect
            except Exception as e:
                result['errors'].append(f'Transpilation error: {str(e)}')
        return result

    def format_query(self, query: str, pretty: bool = True) -> Dict:
        result = self.validate(query)
        if result['is_valid']:
            try:
                parsed = parse_one(query, read=self.dialect)
                result['formatted'] = parsed.sql(pretty=pretty, dialect=self.dialect)
            except Exception as e:
                result['errors'].append(f'Formatting error: {str(e)}')
        return result


