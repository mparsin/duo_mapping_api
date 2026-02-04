#!/usr/bin/env python3
import argparse
import re
from typing import Dict, Tuple, Optional, TextIO

# Matches:
# COMMENT ON TABLE "CSOLineSalespersons" IS 'SalespersonCommission';
RE_COMMENT_TABLE = re.compile(
    r'^\s*COMMENT\s+ON\s+TABLE\s+"(?P<table>[^"]+)"\s+IS\s+\'(?P<comment>(?:\'\'|[^\'])*)\';\s*$',
    re.IGNORECASE
)

# Matches:
# COMMENT ON COLUMN "CSOLineSalespersons"."commissionPercent" IS '...';
RE_COMMENT_COLUMN = re.compile(
    r'^\s*COMMENT\s+ON\s+COLUMN\s+"(?P<table>[^"]+)"\."(?P<col>[^"]+)"\s+IS\s+\'(?P<comment>(?:\'\'|[^\'])*)\';\s*$',
    re.IGNORECASE
)

def pg_escape_literal(s: str) -> str:
    """
    We emit SQL text, not parameterized queries, so we must escape safely.
    Postgres string literal escaping for single quotes is doubling them.
    """
    return s.replace("'", "''")

def normalize_ddl_comment(raw: str) -> str:
    """
    The comment captured from the DDL is already inside single quotes.
    In Postgres dumps, embedded quotes are represented as doubled single-quotes.
    We keep the logical text, then re-escape for output SQL.
    """
    # Convert doubled single quotes to single quote in the logical value
    logical = raw.replace("''", "'")
    return logical.strip()

def write_update_table(out: TextIO, table_name: str, comment: str, schema: str) -> None:
    # Update erp_table.description where name matches.
    out.write(
        f"UPDATE {schema}.erp_table\n"
        f"SET description = '{pg_escape_literal(comment)}', last_modified_at = CURRENT_TIMESTAMP\n"
        f"WHERE name = '{pg_escape_literal(table_name)}';\n"
    )

def write_update_column(out: TextIO, table_name: str, col_name: str, comment: str, schema: str) -> None:
    # Update erp_column.comment using table_id join.
    out.write(
        f"UPDATE {schema}.erp_column c\n"
        f"SET comment = '{pg_escape_literal(comment)}', last_modified_at = CURRENT_TIMESTAMP\n"
        f"FROM {schema}.erp_table t\n"
        f"WHERE c.table_id = t.id\n"
        f"  AND t.name = '{pg_escape_literal(table_name)}'\n"
        f"  AND c.name = '{pg_escape_literal(col_name)}';\n"
    )

def write_insert_missing_table(out: TextIO, table_name: str, comment: str, schema: str) -> None:
    out.write(
        f"INSERT INTO {schema}.erp_table (name, description)\n"
        f"SELECT '{pg_escape_literal(table_name)}', '{pg_escape_literal(comment)}'\n"
        f"WHERE NOT EXISTS (\n"
        f"  SELECT 1 FROM {schema}.erp_table WHERE name = '{pg_escape_literal(table_name)}'\n"
        f");\n"
    )

def write_insert_missing_column(out: TextIO, table_name: str, col_name: str, comment: str, schema: str) -> None:
    out.write(
        f"INSERT INTO {schema}.erp_column (name, comment, table_id)\n"
        f"SELECT '{pg_escape_literal(col_name)}', '{pg_escape_literal(comment)}', t.id\n"
        f"FROM {schema}.erp_table t\n"
        f"WHERE t.name = '{pg_escape_literal(table_name)}'\n"
        f"  AND NOT EXISTS (\n"
        f"    SELECT 1 FROM {schema}.erp_column c\n"
        f"    WHERE c.table_id = t.id AND c.name = '{pg_escape_literal(col_name)}'\n"
        f"  );\n"
    )

def parse_file(
    input_path: str,
    output_path: str,
    schema: str,
    include_table_comments: bool,
    include_column_comments: bool,
    create_missing: bool,
) -> Tuple[int, int]:
    """
    Streams input file line-by-line, extracts COMMENT statements, and writes SQL.
    Returns counts: (tables_found, columns_found).
    """
    tables_found = 0
    cols_found = 0

    with open(input_path, "r", encoding="utf-8", errors="replace") as inp, open(output_path, "w", encoding="utf-8") as out:
        out.write("-- Generated updates from DDL comments\n")
        out.write("BEGIN;\n\n")

        for line in inp:
            m_t = RE_COMMENT_TABLE.match(line)
            if m_t and include_table_comments:
                table = m_t.group("table")
                comment = normalize_ddl_comment(m_t.group("comment"))
                if create_missing:
                    write_insert_missing_table(out, table, comment, schema)
                write_update_table(out, table, comment, schema)
                out.write("\n")
                tables_found += 1
                continue

            m_c = RE_COMMENT_COLUMN.match(line)
            if m_c and include_column_comments:
                table = m_c.group("table")
                col = m_c.group("col")
                comment = normalize_ddl_comment(m_c.group("comment"))
                if create_missing:
                    # If you create missing columns, you probably also want missing tables.
                    # But we will not auto-insert tables here unless table comment existed.
                    # This INSERT will only work if the table already exists in erp_table.
                    write_insert_missing_column(out, table, col, comment, schema)
                write_update_column(out, table, col, comment, schema)
                out.write("\n")
                cols_found += 1
                continue

        out.write("COMMIT;\n")

    return tables_found, cols_found

def main() -> None:
    p = argparse.ArgumentParser(
        description="Parse Postgres DDL COMMENT statements and generate UPDATE SQL for erp_table/erp_column."
    )
    p.add_argument("--input", "-i", required=True, help="Path to the DDL file containing CREATE TABLE / COMMENT statements.")
    p.add_argument("--output", "-o", required=True, help="Path to write generated SQL.")
    p.add_argument("--schema", default="public", help="Schema for erp_table / erp_column (default: public).")
    p.add_argument("--no-table-comments", action="store_true", help="Do not generate updates for erp_table.description.")
    p.add_argument("--no-column-comments", action="store_true", help="Do not generate updates for erp_column.comment.")
    p.add_argument("--create-missing", action="store_true", help="Emit INSERT statements for missing tables/columns before UPDATE.")
    args = p.parse_args()

    tables_found, cols_found = parse_file(
        input_path=args.input,
        output_path=args.output,
        schema=args.schema,
        include_table_comments=not args.no_table_comments,
        include_column_comments=not args.no_column_comments,
        create_missing=args.create_missing,
    )

    print(f"Done. Found {tables_found} table comments and {cols_found} column comments.")
    print(f"Generated SQL: {args.output}")

if __name__ == "__main__":
    main()
