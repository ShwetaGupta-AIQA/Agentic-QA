import argparse
import json
from .analyzer import analyze

def main():
    parser = argparse.ArgumentParser(description="Baseline rule-based requirement analyzer")
    parser.add_argument("requirement")
    args = parser.parse_args()
    try:
        print(json.dumps(analyze(args.requirement), indent=2))
    except ValueError as exc:
        parser.error(str(exc))

if __name__ == "__main__":
    main()
