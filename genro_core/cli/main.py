# Copyright (c) 2025 Softwell Srl, Milano, Italy
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Main entry point for Genro CLI."""

import argparse
import sys
from importlib.metadata import entry_points


def discover_subcommands():
    """Discover subcommands from installed packages using entry points.

    Returns:
        Dictionary mapping subcommand names to their handler functions.
    """
    subcommands = {}

    # Use entry_points() to discover genro CLI plugins
    try:
        # For Python 3.10+
        eps = entry_points(group="genro.cli")
    except TypeError:
        # For Python 3.9
        eps = entry_points().get("genro.cli", [])

    for ep in eps:
        try:
            subcommands[ep.name] = ep.load()
        except Exception as e:
            print(f"Warning: Failed to load subcommand '{ep.name}': {e}", file=sys.stderr)

    return subcommands


def main():
    """Main entry point for genro CLI."""
    parser = argparse.ArgumentParser(
        prog="genro",
        description="Genro Framework - Command-line interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Discover available subcommands
    subcommands = discover_subcommands()

    if not subcommands:
        parser.print_help()
        print("\nNo subcommands available. Install genro packages (e.g., genro-db) to add functionality.")
        sys.exit(1)

    # Add subcommand argument
    subparsers = parser.add_subparsers(
        title="available commands",
        dest="subcommand",
        help="Use 'genro <command> --help' for command-specific help",
    )

    # Register each discovered subcommand
    for name, handler in subcommands.items():
        # Each handler should have a 'register_parser' function
        if hasattr(handler, "register_parser"):
            handler.register_parser(subparsers)

    # Parse arguments
    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(1)

    # Execute the appropriate subcommand
    handler = subcommands[args.subcommand]
    if hasattr(handler, "execute"):
        try:
            handler.execute(args)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Error: Subcommand '{args.subcommand}' has no execute function", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
