# postgres_translator_fixed.py
import logging
from sqlglot import parse_one, expressions as exp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TABLE_MAP = {"jobs": "job_listings", "users": "app_users"}
COLUMN_MAP = {
    "title": "job_title",
    "company_name": "company",
    "location": "location",
    "id": "uid",
    "first_name": "first_name",
    "last_name": "last_name",
    "name": "name",
}

FUNCTION_MAP = {
    "IFNULL": "COALESCE",
    "IF": "__IF_TO_CASE__",
    "DATE_FORMAT": "__DATE_FORMAT__",
    "STR_TO_DATE": "__STR_TO_DATE__",
    "GROUP_CONCAT": "__GROUP_CONCAT__",
    "CONCAT": "__CONCAT__",
    "NOW": "CURRENT_TIMESTAMP",
}

DATE_FORMAT_MAP = {
    "%Y": "YYYY",
    "%y": "YY",
    "%m": "MM",
    "%d": "DD",
    "%H": "HH24",
    "%i": "MI",
    "%s": "SS",
}


def translate_date_format(fmt: str) -> str:
    for k, v in DATE_FORMAT_MAP.items():
        fmt = fmt.replace(k, v)
    return fmt


class SQLTranslator:
    def __init__(self, table_map=TABLE_MAP, column_map=COLUMN_MAP):
        self.table_map = {k.lower(): v for k, v in table_map.items()}
        self.column_map = {k.lower(): v for k, v in column_map.items()}

    def translate(self, sql: str) -> str:
        logger.info("Parsing MySQL SQL...")
        ast = parse_one(sql, read="mysql")
        self._rewrite_tables(ast)
        self._rewrite_columns(ast)
        self._rewrite_functions(ast)
        self._rewrite_intervals(ast)
        return ast.sql(dialect="postgres")

    def _rewrite_tables(self, node):
        for t in node.find_all(lambda e: e.__class__.__name__ == "Table"):
            key = str(t.this).lower()
            if key in self.table_map:
                t.set("this", self.table_map[key])

    def _rewrite_columns(self, node):
        for c in node.find_all(lambda e: e.__class__.__name__ == "Column"):
            name = str(c.this)
            mapped = self.column_map.get(name.lower())
            if mapped:
                c.set("this", mapped)

    def _rewrite_functions(self, node):
        for f in node.find_all(lambda e: e.__class__.__name__ in ["Func", "Anonymous"]):
            try:
                fname = str(f.this).upper()
                if fname not in FUNCTION_MAP:
                    continue
                action = FUNCTION_MAP[fname]

                if action == "__IF_TO_CASE__":
                    args = list(f.expressions)
                    if len(args) >= 3:
                        cond, tv, fv = args[:3]
                        case = exp.Case(
                            this=None, expressions=[exp.When(this=cond, true=tv)], default=fv
                        )
                        f.replace(case)
                elif action == "__DATE_FORMAT__" and len(f.expressions) >= 2:
                    dt_expr, fmt_expr = f.expressions[:2]
                    fmt_val = getattr(fmt_expr, "this", str(fmt_expr))
                    new_node = exp.Anonymous(
                        this="TO_CHAR",
                        expressions=[dt_expr, exp.Literal.string(translate_date_format(fmt_val))],
                    )
                    f.replace(new_node)
                elif action == "__STR_TO_DATE__" and len(f.expressions) >= 2:
                    str_expr, fmt_expr = f.expressions[:2]
                    fmt_val = getattr(fmt_expr, "this", str(fmt_expr))
                    new_node = exp.Anonymous(
                        this="TO_DATE",
                        expressions=[str_expr, exp.Literal.string(translate_date_format(fmt_val))],
                    )
                    f.replace(new_node)
                elif action == "__GROUP_CONCAT__" and f.expressions:
                    args = f.expressions
                    sep = exp.Literal.string(",")
                    new_node = exp.Anonymous(this="STRING_AGG", expressions=[args[0], sep])
                    f.replace(new_node)
                elif action == "__CONCAT__" and f.expressions:
                    args = f.expressions
                    def concat_chain(lst):
                        if len(lst) == 1:
                            return lst[0]
                        return exp.Binary(this=lst[0], op="||", expression=concat_chain(lst[1:]))
                    f.replace(concat_chain(list(args)))
                elif isinstance(action, str) and not action.startswith("__"):
                    f.set("this", action)
            except Exception as e:
                logger.debug(f"Function rewrite error: {e}")

    def _rewrite_intervals(self, node):
        for interval in node.find_all(lambda e: e.__class__.__name__ == "Interval"):
            try:
                val_expr = getattr(interval, "this", None)
                unit_expr = getattr(interval, "unit", None)
                if val_expr is None or unit_expr is None:
                    continue
                value_str = str(getattr(val_expr, "this", val_expr))
                unit_str = str(unit_expr).replace("'", "")
                new_node = exp.Anonymous(this="INTERVAL", expressions=[exp.Literal.string(f"{value_str} {unit_str}")])
                interval.replace(new_node)
            except Exception as e:
                logger.debug(f"Interval rewrite failed: {e}")


if __name__ == "__main__":
    translator = SQLTranslator()
    examples = [
        "SELECT title, company_name, location FROM jobs WHERE location = 'Bangalore'",
        "SELECT j.title AS t, u.name FROM jobs j JOIN users u ON j.posted_by = u.id WHERE u.country = 'IN'",
        "SELECT IFNULL(description,'N/A') as desc FROM jobs",
        "SELECT IF(salary>100000,'high','low') sal_tier FROM jobs",
        "SELECT STR_TO_DATE('2025-10-12','%Y-%m-%d') as dt_val",
        "SELECT CONCAT(first_name,' ',last_name) full_name FROM users",
        "SELECT GROUP_CONCAT(name) names FROM users",
        "SELECT IFNULL(CONCAT(first_name,' ',last_name),'N/A') full_name FROM users",
        "WITH recent_jobs AS (SELECT * FROM jobs WHERE created_at > NOW() - INTERVAL 7 DAY) SELECT title FROM recent_jobs",
    ]
    for q in examples:
        print("\n-- MySQL Query:\n", q)
        try:
            pg = translator.translate(q)
            print("-- Translated PostgreSQL Query:\n", pg)
        except Exception as e:
            print("Translation error:", e)
