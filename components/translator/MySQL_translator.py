import re
from sqlglot import parse_one, exp
from entities.config import GAV_MAPPINGS, SOURCE_TO_TABLE

# Regex for safe unquoted identifier (lowercase, numbers, underscore)
IDENT_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


class SQLTranslator:
    def __init__(self, source: str, global_table_names=None):
        """
        source: name of the target source as defined in entities.config.GAV_MAPPINGS and SOURCE_TO_TABLE
        global_table_names: list of logical global table names used in your global queries (default: ['jobs'])
                            If your project uses more global logical tables, pass them here.
        """
        if source not in GAV_MAPPINGS:
            raise ValueError(f"Source '{source}' is not defined in GAV_MAPPINGS.")
        self.source = source
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
        # Map each provided global logical table name to the source-specific table using SOURCE_TO_TABLE
        target_table = SOURCE_TO_TABLE.get(source)
        table_map = {}
        if target_table:
            for g in self.global_table_names:
                table_map[g] = target_table
        return table_map

    def _should_quote(self, identifier: str) -> bool:
        """Return True if identifier should be quoted for Postgres-like source (Naukri_source)."""
        if identifier is None:
            return False
        return not bool(IDENT_RE.match(identifier))

    def _quote_if_needed(self, identifier: str) -> str:
        if identifier is None:
            return identifier
        if self.source == "Naukri_source":
            if self._should_quote(identifier):
                safe = identifier.replace('"', '""')
                return f'"{safe}"'
            return identifier
        # For MySQL (Linkedin_source) leave as-is (you could add backticks if desired)
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
        """Robust extraction of table name from different AST node shapes."""
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
        """Map & assign a Column node. Handles mapped values 'table.col' or just 'col'."""
        if not isinstance(col_node, exp.Column):
            return
        tbl = col_node.table or parent_table
        mapped = self._map_column_lookup(tbl, col_node.name)

        # If mapped contains a dot, it includes a table -> assign both
        if isinstance(mapped, str) and "." in mapped:
            table_part, col_part = mapped.split(".", 1)
            table_part_mapped = self._map_table(table_part)
            col_assigned = self._quote_if_needed(col_part) if self.source == "Naukri_source" else col_part
            col_node.set("this", col_assigned)
            col_node.set("table", table_part_mapped)
        else:
            # single identifier mapping; quote if needed for Postgres-like
            col_assigned = self._quote_if_needed(mapped) if self.source == "Naukri_source" else mapped
            col_node.set("this", col_assigned)
            if col_node.table:
                col_node.set("table", self._map_table(col_node.table))

    def _replace_recursive(self, node, parent_table=None, visited=None):
        """
        Loop-safe recursive traversal for mapping table and column nodes.
        visited: set of id(node) to avoid infinite recursion on shared AST nodes.
        """
        if visited is None:
            visited = set()

        # Skip non-expression nodes
        if not isinstance(node, exp.Expression):
            return

        # Avoid cycles / repeated nodes
        node_id = id(node)
        if node_id in visited:
            return
        visited.add(node_id)

        # Map Table nodes anywhere in the tree
        if isinstance(node, exp.Table):
            tname = self._extract_table_name(node)
            if tname:
                node.set("this", self._map_table(tname))
            if node.alias:
                parent_table = node.alias

        # Map Column nodes
        if isinstance(node, exp.Column):
            self._assign_column_node(node, parent_table)

        # Handle JOIN nodes (join target may be Table or other)
        if isinstance(node, exp.Join):
            join_target = node.this
            if isinstance(join_target, exp.Table):
                jt_name = self._extract_table_name(join_target)
                if jt_name:
                    join_target.set("this", self._map_table(jt_name))
                if join_target.alias:
                    parent_table = join_target.alias
            elif isinstance(join_target, str):
                # In some AST variants join.this is a string
                try:
                    node.set("this", self._map_table(join_target))
                except Exception:
                    pass
            # Recurse into ON clause
            on_clause = node.args.get("on")
            if on_clause and isinstance(on_clause, exp.Expression):
                self._replace_recursive(on_clause, parent_table, visited)

        # Recurse into node.this (covers Subquery.this, CTE internals, etc.)
        if hasattr(node, "this") and isinstance(getattr(node, "this"), exp.Expression):
            self._replace_recursive(node.this, parent_table, visited)

        # Recurse into expressions list (SELECT projections, function args, etc.)
        for child in getattr(node, "expressions", []) or []:
            if isinstance(child, exp.Expression):
                self._replace_recursive(child, parent_table, visited)

        # Recurse into args dictionary (WHERE, GROUP, HAVING, ORDER BY, etc.)
        for arg in getattr(node, "args", {}).values():
            if isinstance(arg, list):
                for item in arg:
                    if isinstance(item, exp.Expression):
                        self._replace_recursive(item, parent_table, visited)
            elif isinstance(arg, exp.Expression):
                self._replace_recursive(arg, parent_table, visited)

    def translate_query(self, query: str) -> str:
        """
        Parse the input SQL (assumed to use the global schema) and return
        a translated SQL string adapted to the target source.
        """
        try:
            tree = parse_one(query)
            self._replace_recursive(tree)
            # Return MySQL-compatible SQL string (you can change dialect if needed)
            return tree.sql(dialect="mysql")
        except Exception as e:
            raise RuntimeError(f"Failed to translate query: {e}") from e

