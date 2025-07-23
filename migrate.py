#!/usr/bin/env python3
"""
Database migration helper script.

Usage:
    python migrate.py upgrade    # Apply all pending migrations
    python migrate.py current    # Show current migration
    python migrate.py history    # Show migration history
    python migrate.py revision "message"  # Create new migration
"""

import os
import subprocess
import sys


def run_alembic_command(command_args):
    """Run an alembic command with proper environment setup."""
    try:
        # Ensure we're in the project directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        # Run the alembic command
        result = subprocess.run(
            ["alembic"] + command_args, check=True, capture_output=True, text=True
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running alembic command: {e}", file=sys.stderr)
        print(e.stdout)
        print(e.stderr, file=sys.stderr)
        return False
    except FileNotFoundError:
        print(
            "Error: alembic not found. Make sure it's installed and in your PATH.",
            file=sys.stderr,
        )
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "upgrade":
        success = run_alembic_command(["upgrade", "head"])
    elif command == "current":
        success = run_alembic_command(["current"])
    elif command == "history":
        success = run_alembic_command(["history"])
    elif command == "revision":
        if len(sys.argv) < 3:
            print("Error: Please provide a message for the revision")
            print('Usage: python migrate.py revision "Your migration message"')
            sys.exit(1)
        message = sys.argv[2]
        success = run_alembic_command(["revision", "--autogenerate", "-m", message])
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
