#!/usr/bin/env python3

import re
import sys
from pathlib import Path

EXPECTED_MOVS = 1024

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} input.cuasm output.cuasm",
          file=sys.stderr)
    sys.exit(1)

source_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])

lines = source_path.read_text().splitlines(keepends=True)

# LOOK for only MOV Rx, Rx; while preserving control logic, addresses etc.
self_mov = re.compile(
    r"\bMOV\s+R([0-9]+)\s*,\s*R\1\s*;"
)

inside_kernel = False
replacements = 0
output = []

for line in lines:
    # Replace the place holder instructions with NOP in cuasm file.
    if ".section" in line and ".text.nop_kernel" in line:
        inside_kernel = True
    elif inside_kernel and ".section" in line:
        inside_kernel = False

    if inside_kernel and self_mov.search(line):
        line, count = self_mov.subn("NOP;", line)
        replacements += count

    output.append(line)

if replacements != EXPECTED_MOVS:
    print(
        f"Error: found {replacements} self-MOV instructions in "
        f".text.nop_kernel; expected {EXPECTED_MOVS}.",
        file=sys.stderr,
    )
    print(
        "No output written. Inspect the CUASM before patching.",
        file=sys.stderr,
    )
    sys.exit(1)

output_path.write_text("".join(output))
print(f"Patched {replacements} instructions.")
print(f"Wrote {output_path}")