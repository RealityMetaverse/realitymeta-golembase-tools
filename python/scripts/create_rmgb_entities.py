import argparse
from ..factories import create_rmgb_entities_from_directory

entities = []


def main():

    ap = argparse.ArgumentParser(description="Test script to create RMBG entities.")
    ap.add_argument(
        "--in-dir",
        "-in",
        dest="in_dir",
        required=True,
    )

    args = ap.parse_args()

    global entities
    entities = create_rmgb_entities_from_directory(args.in_dir)


if __name__ == "__main__":
    main()
