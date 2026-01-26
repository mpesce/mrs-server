#!/usr/bin/env python3
"""
Initialize the MRS database.

Usage:
    python scripts/init_db.py [database_path]

If no path is provided, uses ./mrs.db
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mrs_server.database import init_database, set_config, close_database


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "./mrs.db"

    print(f"Initializing MRS database at: {db_path}")

    init_database(db_path)

    # Set default configuration if not already set
    print("Database initialized successfully.")
    print("\nTo configure your server, set these environment variables:")
    print("  MRS_SERVER_URL=https://your-domain.com")
    print("  MRS_SERVER_DOMAIN=your-domain.com")
    print("  MRS_ADMIN_EMAIL=admin@your-domain.com")

    close_database()


if __name__ == "__main__":
    main()
