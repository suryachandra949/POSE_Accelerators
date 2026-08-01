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


# Matches a real ".section " directive, but not ".sectioninfo".
section_directive = re.compile(r"^\s*\.section(?:\s+|$)")

# Also works when the kernel name is mangled
target_section = re.compile(
    r"\.text\.[^,\s]*nop_kernel[^,\s]*"
)

# LOOK for only MOV Rx, Rx; while preserving control logic, addresses etc.
self_mov = re.compile(
    r"\bMOV\s+R([0-9]+)\s*,\s*R\1\s*;"
)

inside_kernel = False
replacements = 0
output = []

for line in lines:
    # Replace the place holder instructions with NOP in cuasm file.
    if section_directive.match(line):
        inside_kernel = bool(target_section.search(line))

        if inside_kernel:
            found_kernel_section = True
            print(f"Found kernel section: {line.strip()}")

    if inside_kernel:
        line, count = self_mov.subn("NOP ;", line)
        replacements += count

    output.append(line)

if not found_kernel_section:
    print(
        "Error: could not find a .text section containing nop_kernel.",
        file=sys.stderr,
    )
    print(
        "Run: grep -nE '^\\s*\\.section\\s+' "
        f"{source_path} | grep nop",
        file=sys.stderr,
    )
    sys.exit(1)

if replacements != EXPECTED_MOVS:
    print(
        f"Error: found {replacements} self-MOV instructions "
        f"in nop_kernel; expected {EXPECTED_MOVS}.",
        file=sys.stderr,
    )
    print("No output written.", file=sys.stderr)
    sys.exit(1)

output_path.write_text("".join(output))

print(f"Patched {replacements} self-MOV instructions.")
print(f"Wrote {output_path}")