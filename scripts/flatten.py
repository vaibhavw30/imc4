"""Flatten the modular algo/ source tree into dist/trader.py for IMC submission.

IMC's platform accepts a single Python file. This script concatenates our
modular source in dependency order, strips internal `algo.*` imports, and
deduplicates stdlib + datamodel imports into one header block.

Run from the repo root:  python -m scripts.flatten  (or: python scripts/flatten.py)
"""
from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SOURCES: list[tuple[str, Path]] = [
    ("Logger", REPO_ROOT / "algo" / "logger.py"),
    ("Order book utilities", REPO_ROOT / "algo" / "utils" / "order_book.py"),
    ("Position utilities", REPO_ROOT / "algo" / "utils" / "position.py"),
    ("Strategy base class", REPO_ROOT / "algo" / "strategies" / "base.py"),
    ("Osmium strategy", REPO_ROOT / "algo" / "strategies" / "osmium.py"),
    ("Pepper Root strategy", REPO_ROOT / "algo" / "strategies" / "pepper_root.py"),
    ("Trader", REPO_ROOT / "algo" / "trader.py"),
]

OUTPUT = REPO_ROOT / "dist" / "round2_submission.py"

HEADER = '''"""IMC Prosperity 4 - Round 2 submission (flat single-file build).

Generated from the modular source at algo/* by scripts/flatten.py.
DO NOT EDIT DIRECTLY - edit the source files and re-run the flattener.

Round-1 submission is preserved as-is at dist/bigballers.py and must not
be overwritten by this script.
"""
'''


def _is_main_guard(node: ast.AST) -> bool:
    if not isinstance(node, ast.If):
        return False
    t = node.test
    return (
        isinstance(t, ast.Compare)
        and isinstance(t.left, ast.Name)
        and t.left.id == "__name__"
        and len(t.ops) == 1
        and isinstance(t.ops[0], ast.Eq)
        and len(t.comparators) == 1
        and isinstance(t.comparators[0], ast.Constant)
        and t.comparators[0].value == "__main__"
    )


def parse_file(src: str) -> tuple[list[str], dict[str, set[str]], str]:
    """Split a source file into (plain_imports, from_imports_by_module, body).

    - `plain_imports`: list of `import <module>[ as <alias>]` strings to keep.
    - `from_imports_by_module`: dict mapping module name -> set of "<name>" or
      "<name> as <alias>" strings. Only stdlib / `datamodel` modules; imports
      from `algo.*` or any relative import are dropped.
    - `body`: source with the module docstring, top-level imports, and any
      `if __name__ == "__main__":` block removed.
    """
    tree = ast.parse(src)
    lines = src.splitlines()
    n = len(lines)
    drop = [False] * (n + 2)  # 1-indexed
    plain_imports: list[str] = []
    from_imports: dict[str, set[str]] = {}

    for i, node in enumerate(tree.body):
        if (
            i == 0
            and isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            for ln in range(node.lineno, node.end_lineno + 1):
                drop[ln] = True
        elif isinstance(node, ast.Import):
            for ln in range(node.lineno, node.end_lineno + 1):
                drop[ln] = True
            for alias in node.names:
                suffix = f" as {alias.asname}" if alias.asname else ""
                plain_imports.append(f"import {alias.name}{suffix}")
        elif isinstance(node, ast.ImportFrom):
            for ln in range(node.lineno, node.end_lineno + 1):
                drop[ln] = True
            module = node.module or ""
            if node.level > 0 or module.startswith("algo"):
                continue
            bucket = from_imports.setdefault(module, set())
            for alias in node.names:
                name = alias.name + (f" as {alias.asname}" if alias.asname else "")
                bucket.add(name)
        elif _is_main_guard(node):
            for ln in range(node.lineno, node.end_lineno + 1):
                drop[ln] = True

    kept = [lines[i] for i in range(n) if not drop[i + 1]]
    while kept and not kept[0].strip():
        kept.pop(0)
    while kept and not kept[-1].strip():
        kept.pop()
    return plain_imports, from_imports, "\n".join(kept)


def main() -> None:
    plain_seen: set[str] = set()
    plain_all: list[str] = []
    from_merged: dict[str, set[str]] = {}
    sections: list[tuple[str, Path, str]] = []

    for title, path in SOURCES:
        plain, from_imports, body = parse_file(path.read_text())
        for imp in plain:
            if imp not in plain_seen:
                plain_seen.add(imp)
                plain_all.append(imp)
        for mod, names in from_imports.items():
            from_merged.setdefault(mod, set()).update(names)
        sections.append((title, path, body))

    future_names = from_merged.pop("__future__", set())
    future = [f"from __future__ import {', '.join(sorted(future_names))}"] if future_names else []
    plain = sorted(plain_all)
    from_lines = [
        f"from {mod} import {', '.join(sorted(names))}"
        for mod, names in sorted(from_merged.items())
    ]
    from_imports = from_lines

    parts: list[str] = [HEADER.rstrip(), ""]
    if future:
        parts.extend(future)
        parts.append("")
    if plain:
        parts.extend(plain)
        parts.append("")
    if from_imports:
        parts.extend(from_imports)
        parts.append("")

    for title, path, body in sections:
        rel = path.relative_to(REPO_ROOT)
        parts.append(f"# --- {title} (from {rel}) ---")
        parts.append("")
        parts.append(body)
        parts.append("")

    out = "\n".join(parts).rstrip() + "\n"

    ast.parse(out)  # fail fast if we produced something unparseable

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(out)

    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)}  ({len(out):,} bytes, {out.count(chr(10))} lines)")
    print(f"imports: {len(plain)} plain + {len(from_imports)} from-import + {len(future)} __future__")


if __name__ == "__main__":
    main()
