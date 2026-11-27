import json, sys
nb = json.load(open(sys.argv[1], encoding="utf-8"))
code = "\n\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
code = "\n".join(l for l in code.splitlines() if not l.strip().startswith("%"))
exec(compile(code, sys.argv[1], "exec"), {"__name__": "__main__"})
