"""Print text outputs of an executed notebook (for review)."""
import sys, nbformat
nb = nbformat.read(sys.argv[1], as_version=4)
skip = set(int(x) for x in sys.argv[2].split(",")) if len(sys.argv) > 2 else set()
for i, c in enumerate(nb.cells):
    if c.cell_type != "code" or i in skip:
        continue
    for o in c.get("outputs", []):
        if o.output_type == "error":
            print(f"--- [{i}] ERROR", o.ename, o.evalue)
        txt = o.get("text") or o.get("data", {}).get("text/plain")
        if txt:
            print(f"--- [{i}] {c.source.splitlines()[0][:70]}")
            print(txt if len(txt) < 3500 else txt[:3500] + "\n...[truncated]")
