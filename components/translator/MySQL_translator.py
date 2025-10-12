# D:\Projects\NextMove\components\translator\SQLTranslator.py
import re
from sqlglot import parse_one, exp
from entities.config import GAV_MAPPINGS, SOURCE_TO_TABLE

# Regex for safe unquoted identifier (lowercase, numbers, underscore)
IDENT_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

class SQLTranslator:
    def __init__(self, source: str, global_table_names=None, dialect: str = "mysql"):
        """
        source: name of the target source as defined in entities.config.GAV_MAPPINGS and SOURCE_TO_TABLE
        global_table_names: list of logical global table names used in your global queries
        dialect: 'mysql' or 'postgres'
        """
        if source not in GAV_MAPPINGS:
            raise ValueError(f"Source '{source}' is not defined in GAV_MAPPINGS.")
        if dialect.lower() not in ("mysql", "postgres"):
            raise ValueError("Dialect must be either 'mysql' or 'postgres'")

        self.source = source
        self.dialect = dialect.lower()
        self.column_mapping = self._generate_column_mapping(source)
        self.global_table_names = global_table_names or ["jobs"]
        self.table_mapping = self._generate_table_mapping(source)

    def _generate_column_mapping(self, source):
        mapping = {}
        gav = GAV_MAPPINGS.get(source, {})
        for global_col, source_col in gav.items():
            if source_col:
                mapping[global_col] = source_col
        return mapping

    def _generate_table_mapping(self, source):
        target_table = SOURCE_TO_TABLE.get(source)
        table_map = {}
        if target_table:
            for g in self.global_table_names:
                table_map[g] = target_table
        return table_map

    def _should_quote(self, identifier: str) -> bool:
        """Return True if identifier should be quoted (Postgres: reserved or contains spaces)."""
        if identifier is None:
            return False
        # Only Postgres dialect uses quotes for non-simple identifiers
        if self.dialect == "postgres":
            return not bool(IDENT_RE.match(identifier))
        # MySQL: only quote if contains spaces or special chars
        if self.dialect == "mysql":
            return not bool(re.match(r"^[A-Za-z0-9_]+$", identifier))
        return False

    def _quote_if_needed(self, identifier: str) -> str:
        if identifier is None:
            return identifier
        if self._should_quote(identifier):
            if self.dialect == "postgres":
                safe = identifier.replace('"', '""')
                return f'"{safe}"'
            elif self.dialect == "mysql":
                return f"`{identifier}`"
        return identifier

    def _map_table(self, table_name: str) -> str:
        if not table_name:
            return table_name
        mapped = self.table_mapping.get(table_name, table_name)
        return self._quote_if_needed(mapped)

    def _map_column_lookup(self, table, col):
        # Prefer table-qualified mapping (table.col) then unqualified column mapping
        if table:
            fq = f"{table}.{col}"
            if fq in self.column_mapping:
                return self.column_mapping[fq]
        return self.column_mapping.get(col, col)

    def _extract_table_name(self, node):
        if node is None:
            return None
        if isinstance(node, str):
            return node
        if isinstance(node, exp.Table):
            t = node.this
            if isinstance(t, str):
                return t
            if hasattr(t, "name"):
                return t.name
            try:
                return str(t)
            except Exception:
                return None
        if hasattr(node, "name"):
            return node.name
        try:
            return str(node)
        except Exception:
            return None

    def _assign_column_node(self, col_node: exp.Column, parent_table):
        if not isinstance(col_node, exp.Column):
            return
        tbl = col_node.table or parent_table
        mapped = self._map_column_lookup(tbl, col_node.name)

        if isinstance(mapped, str) and "." in mapped:
            table_part, col_part = mapped.split(".", 1)
            table_part_mapped = self._map_table(table_part)
            col_assigned = self._quote_if_needed(col_part)
            col_node.set("this", col_assigned)
            col_node.set("table", table_part_mapped)
        else:
            col_assigned = self._quote_if_needed(mapped)
            col_node.set("this", col_assigned)
            if col_node.table:
                col_node.set("table", self._map_table(col_node.table))

    def _replace_recursive(self, node, parent_table=None, visited=None):
        if visited is None:
            visited = set()
        if not isinstance(node, exp.Expression):
            return
        node_id = id(node)
        if node_id in visited:
            return
        visited.add(node_id)

        if isinstance(node, exp.Table):
            tname = self._extract_table_name(node)
            if tname:
                node.set("this", self._map_table(tname))
            if node.alias:
                parent_table = node.alias

        if isinstance(node, exp.Column):
            self._assign_column_node(node, parent_table)

        if isinstance(node, exp.Join):
            join_target = node.this
            if isinstance(join_target, exp.Table):
                jt_name = self._extract_table_name(join_target)
                if jt_name:
                    join_target.set("this", self._map_table(jt_name))
                if join_target.alias:
                    parent_table = join_target.alias
            elif isinstance(join_target, str):
                try:
                    node.set("this", self._map_table(join_target))
                except Exception:
                    pass
            on_clause = node.args.get("on")
            if on_clause and isinstance(on_clause, exp.Expression):
                self._replace_recursive(on_clause, parent_table, visited)

        if hasattr(node, "this") and isinstance(getattr(node, "this"), exp.Expression):
            self._replace_recursive(node.this, parent_table, visited)

        for child in getattr(node, "expressions", []) or []:
            if isinstance(child, exp.Expression):
                self._replace_recursive(child, parent_table, visited)

        for arg in getattr(node, "args", {}).values():
            if isinstance(arg, list):
                for item in arg:
                    if isinstance(item, exp.Expression):
                        self._replace_recursive(item, parent_table, visited)
            elif isinstance(arg, exp.Expression):
                self._replace_recursive(arg, parent_table, visited)

    def translate_query(self, query: str) -> str:
        """
        Translate a query from global schema to target source SQL.
        Returns SQL string compatible with the specified dialect.
        """
        try:
            tree = parse_one(query)
            self._replace_recursive(tree)
            return tree.sql(dialect=self.dialect)
        except Exception as e:
            raise RuntimeError(f"Failed to translate query: {e}") from e
