#!/usr/bin/env python3
"""Run the public news feed web server.

Usage:
    python run_web.py [--port PORT] [--host HOST] [--debug]

Default: http://0.0.0.0:8502
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.web.app import app


def main():
    parser = argparse.ArgumentParser(description="Run public news feed server")
    parser.add_argument("--port", type=int, default=8502, help="Port number (default: 8502)")
    parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    print(f"Starting public news feed server on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
