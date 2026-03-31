import argparse
import sys
from .utils import download_models as _download_models

def main():
    parser = argparse.ArgumentParser(
        description="FinGuard CLI — The Open-Source LLM Firewall for Financial AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  finguard download-models
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # download-models
    subparsers.add_parser(
        "download-models", 
        help="Pre-cache all ONNX weights and models for built-in policies to ensure instant startup."
    )
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.command == "download-models":
        _download_models()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
