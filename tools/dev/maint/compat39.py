"""Runtime Python 3.9 hazards an ast feature_version parse doesn't catch."""
import ast, glob, os, sys, re
A = sys.argv[1]
NEW_ATTRS = {"bit_count": "3.10", "pairwise": "3.10", "removeprefix": "3.9", "removesuffix": "3.9",
             "UTC": "3.11", "fromisoformat": "?", "batched": "3.12", "anext": "3.10", "aiter": "3.10"}
NEW_MODS = {"tomllib": "3.11", "zoneinfo": "3.9", "graphlib": "3.9"}
issues = 0
for p in sorted(glob.glob(os.path.join(A, "*.py"))):
    src = open(p, encoding="utf-8").read()
    tree = ast.parse(src)
    fut = any(isinstance(n, ast.ImportFrom) and n.module == "__future__" and
              any(a.name == "annotations" for a in n.names) for n in tree.body)
    name = os.path.basename(p)
    def bitor(node):
        return any(isinstance(x, ast.BinOp) and isinstance(x.op, ast.BitOr) for x in ast.walk(node))
    for n in ast.walk(tree):
        # annotations evaluated at runtime without the future import
        if not fut:
            anns = []
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                anns += [a.annotation for a in n.args.args + n.args.kwonlyargs + n.args.posonlyargs if a.annotation]
                if n.args.vararg and n.args.vararg.annotation: anns.append(n.args.vararg.annotation)
                if n.returns: anns.append(n.returns)
            if isinstance(n, ast.AnnAssign):
                anns.append(n.annotation)
            for a in anns:
                if bitor(a):
                    issues += 1; print(f"{name}:{a.lineno}: X | Y annotation without __future__ annotations")
        # runtime unions anywhere: isinstance(x, A | B)
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) in ("isinstance", "issubclass") and len(n.args) == 2 and bitor(n.args[1]):
            issues += 1; print(f"{name}:{n.lineno}: isinstance with X | Y")
        if isinstance(n, ast.Call):
            for kw in n.keywords:
                if kw.arg == "strict" and getattr(n.func, "id", None) == "zip":
                    issues += 1; print(f"{name}:{n.lineno}: zip(strict=) 3.10")
                if kw.arg in ("slots", "kw_only") and "dataclass" in ast.dump(n.func):
                    issues += 1; print(f"{name}:{n.lineno}: dataclass({kw.arg}=) 3.10")
        if isinstance(n, ast.Attribute) and n.attr in ("bit_count", "pairwise", "UTC", "batched"):
            issues += 1; print(f"{name}:{n.lineno}: .{n.attr} needs {NEW_ATTRS[n.attr]}")
        if isinstance(n, ast.Name) and n.id in ("anext", "aiter"):
            issues += 1; print(f"{name}:{n.lineno}: {n.id} 3.10")
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
            for m in mods:
                if m.split(".")[0] in ("tomllib",):
                    issues += 1; print(f"{name}:{n.lineno}: import {m} 3.11")
        if isinstance(n, ast.With) and len(n.items) > 1:
            seg = ast.get_source_segment(src, n) or ""
            if re.match(r"\s*with\s*\(", seg):
                issues += 1; print(f"{name}:{n.lineno}: parenthesized with 3.10")
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id in ("TypeAlias", "ParamSpec", "Self"):
            issues += 1; print(f"{name}:{n.lineno}: typing {n.value.id}")
    for m in re.finditer(r"from typing import ([^\n]+)", src):
        for t in ("TypeAlias", "ParamSpec", "Self", "TypeGuard", "Concatenate", "LiteralString", "Never", "assert_never"):
            if re.search(rf"\b{t}\b", m.group(1)):
                issues += 1; print(f"{name}: from typing import {t} (3.10+)")
print("compat-3.9:", "OK" if not issues else f"{issues} issue(s)")
