r"""Extract and rename COPY blocks from a legacy GOR_PATRIMONIO cluster dump.

Reads the dump file line by line, captures COPY ... FROM stdin blocks for
the 7 B3 tables, rewrites the target schema to the value passed via
--schema, and streams the result to stdout for piping into psql.

Usage
-----
python3 bin/migrate_legacy.py path/to/wealth.sql --schema <your-schema> \
    | docker compose exec -T \
        -e PGPASSWORD="$DB_PASSWORD" \
        postgresql \
        psql -U "$DB_USER" -d "$DB_NAME" --set ON_ERROR_STOP=on
"""

from __future__ import annotations

import argparse
import re
import sys


_TABLE_MAP: dict[str, str] = {
    "bonificacao_acoes": "b3_bonificacao_acoes",
    "movimentacao": "b3_movimentacao",
    "negociacao": "b3_negociacao",
    "posicao_acoes": "b3_posicao_acoes",
    "posicao_emprestimos": "b3_posicao_emprestimos",
    "proventos_recebidos": "b3_proventos_recebidos",
    "reembolso_emprestimos": "b3_reembolso_emprestimos",
}


def _normalize_nulls(line: str) -> str:
    r"""Replace B3 legacy null sentinels ("-") with the PostgreSQL COPY null marker.

    The dash "-" is used in B3 annual-report exports to represent N/A values in
    date and numeric columns.  PostgreSQL COPY text format represents NULL as "\N";
    replacing at tab boundaries avoids touching legitimate dash characters inside
    string fields (e.g. contract numbers like "2022122200409620420001-1").
    """
    fields = line.rstrip("\n").split("\t")
    normalized = ["\\N" if f == "-" else f for f in fields]
    return "\t".join(normalized) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dump_file", help="Path to the legacy .sql cluster dump")
    parser.add_argument(
        "--schema",
        default="public",
        help="Target PostgreSQL schema (default: public)",
    )
    return parser.parse_args()


def main() -> None:
    """Parse arguments and stream renamed COPY blocks to stdout."""
    args = _parse_args()
    str_schema = args.schema

    # Brazilian date format (DD/MM/YYYY) used throughout the legacy dump.
    sys.stdout.write("SET datestyle = 'ISO, DMY';\n")

    # Wipe any partial data from a previous run before re-importing.
    for new_name in _TABLE_MAP.values():
        sys.stdout.write(f"TRUNCATE TABLE {str_schema}.{new_name} CASCADE;\n")

    in_copy = False
    skip_block = False
    set_loaded: set[str] = set()  # prevents re-importing duplicate COPY blocks

    with open(args.dump_file) as f:
        for line in f:
            if line.startswith("COPY public.") or line.startswith("COPY "):
                match = re.match(r"COPY (?:public\.)?(\w+) ", line)
                if match:
                    old_name = match.group(1)
                    new_name = _TABLE_MAP.get(old_name)
                    if new_name and old_name not in set_loaded:
                        set_loaded.add(old_name)
                        old_token = f"public.{old_name} " if "public." in line else f"{old_name} "
                        sys.stdout.write(
                            line.replace(old_token, f"{str_schema}.{new_name} ", 1)
                        )
                        in_copy = True
                        skip_block = False
                    else:
                        in_copy = True
                        skip_block = True
            elif in_copy:
                if line.rstrip("\n") == "\\.":
                    if not skip_block:
                        sys.stdout.write(line)
                    in_copy = False
                    skip_block = False
                elif not skip_block:
                    sys.stdout.write(_normalize_nulls(line))


if __name__ == "__main__":
    main()
