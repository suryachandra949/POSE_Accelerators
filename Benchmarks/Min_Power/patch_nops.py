#!/usr/bin/env python3

import re
import sys
from pathlib import Path

EXPECTED_NOPS = 1024

if len(sys.argv) != 3:
    print(
        f"Usage: {sys.argv[0]} input.cuasm output.cuasm",
        file=sys.stderr,
    )
    sys.exit(1)

input_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])

lines = input_path.read_text().splitlines(keepends=True)

section_directive = re.compile(r"^\s*\.section(?:\s+|$)")
target_section = re.compile(r"\.text\.[^,\s]*nop_kernel[^,\s]*")

# Any SASS instruction line with an address.
instruction_line = re.compile(
    r"/\*([0-9a-fA-F]+)\*/\s+"
)

# MOV R7, R7 ;
self_mov = re.compile(
    r"\bMOV\s+R([0-9]+)\s*,\s*R\1\s*;"
)

inside_kernel = False
found_kernel = False

runs: list[list[tuple[int, int]]] = []
current_run: list[tuple[int, int]] = []

def finish_run() -> None:
    global current_run

    if current_run:
        runs.append(current_run)
        current_run = []

for line_number, line in enumerate(lines):
    if section_directive.match(line):
        finish_run()

        inside_kernel = bool(target_section.search(line))

        if inside_kernel:
            found_kernel = True
            print(f"Found kernel section: {line.strip()}")

        continue

    if not inside_kernel:
        continue

    instruction_match = instruction_line.search(line)

    # Blank lines, labels and comments do not interrupt a run.
    if not instruction_match:
        continue

    address = int(instruction_match.group(1), 16)

    if self_mov.search(line):
        current_run.append((line_number, address))
    else:
        # A real intervening SASS instruction ends the consecutive run.
        finish_run()

finish_run()

if not found_kernel:
    print(
        "Error: could not find nop_kernel text section.",
        file=sys.stderr,
    )
    sys.exit(1)

runs.sort(key=len, reverse=True)

print("Largest consecutive self-MOV runs:")

for run in runs[:10]:
    print(
        f"  count={len(run):4d} "
        f"start=0x{run[0][1]:x} "
        f"end=0x{run[-1][1]:x}"
    )

exact_runs = [run for run in runs if len(run) == EXPECTED_NOPS]

if len(exact_runs) != 1:
    print(
        f"Error: expected one consecutive run of exactly "
        f"{EXPECTED_NOPS} self-MOVs, found {len(exact_runs)}.",
        file=sys.stderr,
    )

    if runs:
        print(
            f"Longest run contains {len(runs[0])} instructions.",
            file=sys.stderr,
        )

    print("No output written.", file=sys.stderr)
    sys.exit(1)

placeholder_run = exact_runs[0]
lines_to_patch = {line_number for line_number, _ in placeholder_run}

for line_number in lines_to_patch:
    lines[line_number], count = self_mov.subn(
        "NOP ;",
        lines[line_number],
        count=1,
    )

    if count != 1:
        print(
            f"Internal error patching line {line_number + 1}.",
            file=sys.stderr,
        )
        sys.exit(1)

output_path.write_text("".join(lines))

print(
    f"Patched {len(lines_to_patch)} consecutive self-MOVs "
    f"from 0x{placeholder_run[0][1]:x} "
    f"through 0x{placeholder_run[-1][1]:x}."
)
print(f"Wrote {output_path}")