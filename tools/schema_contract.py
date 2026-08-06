"""Static check: every column a module names against a table must exist in the live schema.

Parses Python source with ``ast`` and walks supabase-py builder chains rooted at
``.table("<name>")``, collecting the column names used in ``.select()``, filter methods
(``.eq()``, ``.order()``, …) and ``insert``/``update``/``upsert`` payload dicts. Each name is
checked against a snapshot produced by ``tools/introspect_schema.py``.

Why AST and not regex
---------------------
A regex over source text cannot tell a column name from a response-dict key. An early regex
version of this check reported ``"session"``, ``"cycles"`` and ``"ok"`` as missing columns —
roughly two false positives for every true hit — because api.py builds response payloads with
dict literals that look identical to insert payloads. Walking the AST scopes every name to a
genuine builder chain, which removes that entire class of noise.

Usage:
    python tools/schema_contract.py api.py supabase/live_schema.json
"""
import ast
import json
import sys
from pathlib import Path

# supabase-py/postgrest filter methods whose FIRST positional arg is a column name.
FILTER_METHODS = {
    "eq", "neq", "gt", "gte", "lt", "lte", "like", "ilike",
    "is_", "in_", "contains", "contained_by", "order",
}
# Methods whose first positional arg is a payload dict keyed by column name.
PAYLOAD_METHODS = {"insert", "update", "upsert"}


class Violation:
    def __init__(self, line, table, column, kind):
        self.line, self.table, self.column, self.kind = line, table, column, kind

    def __str__(self):
        return f"line {self.line}: {self.table}.{self.column} ({self.kind}) not in live schema"


def _base_table(node):
    """Walk down a call chain and return the table name from its `.table("X")` root."""
    cur = node
    while True:
        if isinstance(cur, ast.Call):
            if not isinstance(cur.func, ast.Attribute):
                return None
            if cur.func.attr == "table" and cur.args:
                arg = cur.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    return arg.value
                return None
            cur = cur.func.value
        elif isinstance(cur, ast.Attribute):
            cur = cur.value
        else:
            return None


def _split_select(spec):
    """Yield (embedded_table_or_None, column) pairs from a PostgREST select string.

    Handles `a, b`, aliases (`alias:col`), and embedded resources (`athletes(name, id)`,
    `athletes!inner(name)`). Embedded columns are attributed to the embedded table.
    """
    depth, buf, out = 0, "", []
    for ch in spec:
        if ch == "," and depth == 0:
            out.append(buf)
            buf = ""
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        buf += ch
    out.append(buf)

    for part in out:
        part = part.strip()
        if not part or part == "*":
            continue
        if "(" in part and part.endswith(")"):
            head, inner = part.split("(", 1)
            inner = inner[:-1]
            embedded = head.split("!")[0].split(":")[-1].strip()
            for sub in _split_select(inner):
                # An embedded block's columns belong to the embedded table, not the parent.
                yield (sub[0] or embedded, sub[1])
            continue
        if ":" in part:
            part = part.split(":", 1)[1].strip()
        part = part.split("->")[0].split("::")[0].strip()  # json path / cast
        if part and part != "*":
            yield (None, part)


def find_violations(source: str, schema: dict):
    """Return [Violation] for every column reference absent from `schema`."""
    tree = ast.parse(source)
    violations = []

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        method = node.func.attr
        table = _base_table(node)
        if table is None:
            continue

        if table not in schema:
            violations.append(Violation(node.lineno, table, "*", "table missing"))
            continue
        cols = schema[table]

        if method == "select" and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                for embedded, col in _split_select(arg.value):
                    target = embedded or table
                    # An embedded table we have no snapshot for is not a violation.
                    if target in schema and col not in schema[target]:
                        violations.append(Violation(node.lineno, target, col, "select"))

        elif method in FILTER_METHODS and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                col = arg.value.split("->")[0].strip()
                if col and col not in cols:
                    violations.append(Violation(node.lineno, table, col, method))

        elif method in PAYLOAD_METHODS and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Dict):
                for k in arg.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        if k.value not in cols:
                            violations.append(Violation(k.lineno, table, k.value, method))

    return sorted(violations, key=lambda v: v.line)


def unused_columns(source: str, schema: dict):
    """Columns present live but never named anywhere in the source (dead-schema leads)."""
    tree = ast.parse(source)
    seen = {t: set() for t in schema}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        table = _base_table(node)
        if table not in schema:
            continue
        if node.func.attr == "select" and node.args and isinstance(node.args[0], ast.Constant):
            for embedded, col in _split_select(str(node.args[0].value)):
                seen.setdefault(embedded or table, set()).add(col)
        elif node.func.attr in FILTER_METHODS and node.args and isinstance(node.args[0], ast.Constant):
            seen[table].add(str(node.args[0].value))
        elif node.func.attr in PAYLOAD_METHODS and node.args and isinstance(node.args[0], ast.Dict):
            for k in node.args[0].keys:
                if isinstance(k, ast.Constant):
                    seen[table].add(str(k.value))
    return {t: sorted(set(cols) - seen.get(t, set())) for t, cols in schema.items()}


def main():
    src_path, schema_path = Path(sys.argv[1]), Path(sys.argv[2])
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    source = src_path.read_text(encoding="utf-8")

    violations = find_violations(source, schema)
    print(f"=== {src_path} vs {schema_path} ===")
    if not violations:
        print("no violations")
    for v in violations:
        print(f"{src_path}:{v.line}  {v.table}.{v.column}  [{v.kind}]")

    print("\n=== columns live but never referenced ===")
    for table, cols in sorted(unused_columns(source, schema).items()):
        if cols:
            print(f"{table}: {', '.join(cols)}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
