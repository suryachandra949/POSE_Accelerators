#!/usr/bin/env python3

import re
import sys
from pathlib import Path

START_ADDRESS = 0x01F0
END_ADDRESS = 0x41E0
EXPECTED_PATCHES = 1024

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} input.cuasm output.cuasm",
          file=sys.stderr)
    sys.exit(1)

input_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])

section_re = re.compile(r"^\s*\.section(?:\s+|$)")
kernel_re = re.compile(r"\.text\.nop_kernel(?:[,\s]|$)")
address_re = re.compile(r"/\*([0-9a-fA-F]+)\*/")

# Patch only the register used by the inline-assembly placeholder.
placeholder_re = re.compile(
    r"\bMOV\s+R8\s*,\s*R8\s*;"
)

lines = input_path.read_text().splitlines(keepends=True)

inside_kernel = False
patch_count = 0
output_lines = []

for line_number, line in enumerate(lines, start=1):
    if section_re.match(line):
        inside_kernel = bool(kernel_re.search(line))

    if inside_kernel:
        address_match = address_re.search(line)

        if address_match:
            address = int(address_match.group(1), 16)

            if START_ADDRESS <= address <= END_ADDRESS:
                if not placeholder_re.search(line):
                    print(
                        f"Error: expected MOV R8, R8 at "
                        f"address 0x{address:04x}, source line "
                        f"{line_number}:",
                        file=sys.stderr,
                    )
                    print(line.rstrip(), file=sys.stderr)
                    print("No output written.", file=sys.stderr)
                    sys.exit(1)

                line, replacements = placeholder_re.subn(
                    "NOP ;",
                    line,
                    count=1,
                )
                patch_count += replacements

    output_lines.append(line)

if patch_count != EXPECTED_PATCHES:
    print(
        f"Error: patched {patch_count} instructions; "
        f"expected {EXPECTED_PATCHES}.",
        file=sys.stderr,
    )
    print("No output written.", file=sys.stderr)
    sys.exit(1)

output_path.write_text("".join(output_lines))

print(
    f"Patched exactly {patch_count} MOV R8, R8 instructions "
    f"from 0x{START_ADDRESS:04x} through "
    f"0x{END_ADDRESS:04x}."
)
print(f"Wrote {output_path}")