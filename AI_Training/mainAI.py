"""
main.py — CLI entry point
─────────────────────────
Menu-driven launcher for all pipeline stages.

  1  Extract & Build Dataset
  2  Train Model
  3  Realtime Test
  0  Exit
"""

import os
import sys

MENU = """
╔══════════════════════════════════════╗
║   YOLOv8 + TCN  Fall Detector        ║
╠══════════════════════════════════════╣
║  1.  Extract & Build Dataset         ║
║  2.  Train Model                     ║
║  0.  Exit                            ║
╚══════════════════════════════════════╝
"""

EXTRACT_STEPS = [
    ("Extract UR dataset",   "python scripts/extract_ur.py"),
    ("Extract LE2I dataset", "python scripts/extract_le2i.py"),
    ("Build dataset",        "python scripts/build_dataset.py"),
    ("Merge datasets",       "python scripts/merge_datasets.py"),
]

COMMANDS = {
    "2": ("Train Model",   "python -m lstm.train"),
}


def run(label: str, cmd: str) -> None:
    print(f"\n{'='*44}")
    print(f"▶  {label}")
    print(f"{'='*44}\n")
    ret = os.system(cmd)
    if ret != 0:
        print(f"\n✖  '{label}' exited with code {ret}.\n")
    else:
        print(f"\n✔  '{label}' completed successfully.\n")


def main() -> None:
    while True:
        print(MENU)
        choice = input("Select [0-2]: ").strip()

        if choice == "0":
            print("Bye.")
            sys.exit(0)

        elif choice == "1":
            for label, cmd in EXTRACT_STEPS:
                run(label, cmd)
            print("✔ Extract & Build pipeline complete.\n")

        elif choice == "2":
            label, cmd = COMMANDS["2"]
            run(label, cmd)

        else:
            print("✖ Invalid option. Please enter 0, 1, or 2.\n")


if __name__ == "__main__":
    main()