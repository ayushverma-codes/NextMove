import re
from sqlglot import parse_one, exp
from entities.config import GAV_MAPPINGS

# Regex for safe unquoted identifier (lowercase, numbers, underscore)
IDENT_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

class SQLTranslator:
    def __init__(self, source: str, global_table_names=None, target_table_name: str = None, dialect: str = "mysql"):
        """
        source: name of the target source (e.g., 'Linkedin_source')
        target_table_name: The actual physical table name (e.g., 'jobs')
        """
        if source not in GAV_MAPPINGS:
            raise ValueError(f"Source '{source}' is not defined in GAV_MAPPINGS.")
        if dialect.lower() not in ("mysql", "postgres"):
            raise ValueError("Dialect must be either 'mysql' or 'postgres'")

        self.source = source
        self.dialect = dialect.lower()
        self.target_table_name = target_table_name

        # --- FIX: Add 'job_listings' and 'job_postings' to the detection list ---
        # This ensures that if the LLM generates 'FROM job_listings', we catch it and map it.
        self.global_table_names = global_table_names or [
            "jobs", 
            "job_listings", 
            "job_postings", 
            "Global_Job_Postings",
            "unified_job_posting"
        ]
        
        self.column_mapping = self._generate_column_mapping(source)
        self.table_mapping = self._generate_table_mapping()

    def _generate_column_mapping(self, source):
        mapping = {}
        gav = GAV_MAPPINGS.get(source, {})
        for global_col, source_col in gav.items():
            if source_col:
                # Normalize to lowercase for consistent lookup
                mapping[global_col.lower()] = source_col
        return mapping

    def _generate_table_mapping(self):
        """
        Maps ALL detected global table variations to the single target table.
        """
        table_map = {}
        if self.target_table_name:
            for g in self.global_table_names:
                # Map both raw and lowercase versions to be safe
                table_map[g] = self.target_table_name
                table_map[g.lower()] = self.target_table_name
        return table_map

    def _should_quote(self, identifier: str) -> bool:
        if identifier is None:
            return False
        if self.dialect == "postgres":
            return not bool(IDENT_RE.match(identifier))
        if self.dialect == "mysql":
            # Quote if it contains spaces or special chars
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
        
        # Case-insensitive lookup
        lower_name = table_name.lower()
        
        # Check if this table name is in our "Global List" that needs mapping
        # OR if we simply have a direct mapping for it
        mapped_name = self.table_mapping.get(lower_name, self.table_mapping.get(table_name))
        
        if mapped_name:
            return self._quote_if_needed(mapped_name)
        
        # If not found in mapping, return original (quoted if needed)
        return self._quote_if_needed(table_name)

    def _map_column_lookup(self, table, col):
        # 1. Try fully qualified lookup (table.col)
        if table:
            # We don't rely on table name here for mapping keys, usually just global column name
            pass
        
        # 2. Try simple column lookup (case-insensitive input)
        return self.column_mapping.get(col.lower(), col)

    def _extract_table_name(self, node):
        if node is None: return None
        if isinstance(node, str): return node
        if isinstance(node, exp.Table):
            return node.name
        return str(node)

    def _assign_column_node(self, col_node: exp.Column, parent_table):
        if not isinstance(col_node, exp.Column):
            return
        
        # Get mapped column name
        mapped_col_name = self._map_column_lookup(None, col_node.name)

        # If specific source requires table prefix (e.g. "t1.col"), split it
        if isinstance(mapped_col_name, str) and "." in mapped_col_name:
            table_part, col_part = mapped_col_name.split(".", 1)
            col_node.set("this", exp.Identifier(this=col_part, quoted=self._should_quote(col_part)))
            col_node.set("table", exp.Identifier(this=table_part, quoted=self._should_quote(table_part)))
        else:
            # Update the column name
            col_node.set("this", exp.Identifier(this=mapped_col_name, quoted=self._should_quote(mapped_col_name)))
            
            # IMPORTANT: If the column had a table alias/name attached (e.g. job_listings.title),
            # we must update that table identifier to the LOCAL table name too.
            if col_node.table:
                mapped_table = self._map_table(col_node.table)
                # Remove quotes for the Identifier constructor, it adds them based on quoted=True
                clean_table = mapped_table.replace("`", "").replace('"', "")
                col_node.set("table", exp.Identifier(this=clean_table, quoted=True))

    def _replace_recursive(self, node, parent_table=None, visited=None):
        if visited is None:
            visited = set()
        if not isinstance(node, exp.Expression):
            return
        
        node_id = id(node)
        if node_id in visited:
            return
        visited.add(node_id)

        # 1. Handle Table Nodes (FROM clauses, JOINs)
        if isinstance(node, exp.Table):
            tname = self._extract_table_name(node)
            if tname:
                mapped = self._map_table(tname)
                # Update node
                node.set("this", exp.Identifier(this=mapped.replace("`", "").replace('"', ""), quoted=True))
            if node.alias:
                parent_table = node.alias

        # 2. Handle Column Nodes (SELECT list, WHERE clauses)
        if isinstance(node, exp.Column):
            self._assign_column_node(node, parent_table)

        # 3. Recurse into args/expressions
        for arg in node.args.values():
            if isinstance(arg, list):
                for item in arg:
                    if isinstance(item, exp.Expression):
                        self._replace_recursive(item, parent_table, visited)
            elif isinstance(arg, exp.Expression):
                self._replace_recursive(arg, parent_table, visited)

    def translate_query(self, query: str) -> str:
        """
        Translate a query from global schema to target source SQL using sqlglot.
        """
        try:
            # Parse
            tree = parse_one(query)
            
            # Transform
            self._replace_recursive(tree)
            
            # Generate SQL
            return tree.sql(dialect=self.dialect)
            
        except Exception as e:
            print(f"[Translator Error] {e}")
            return query