import argparse
from ..factories import create_rmgb_entries_from_directory

entries = []


def main():

    ap = argparse.ArgumentParser(description="Test script.")
    ap.add_argument(
        "--out-dir",
        "-o",
        dest="out_dir",
        required=True,
    )

    args = ap.parse_args()

    global entries
    entries = create_rmgb_entries_from_directory(args.out_dir)


if __name__ == "__main__":
    main()
