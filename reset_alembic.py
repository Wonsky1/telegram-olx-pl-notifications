#!/usr/bin/env python3
"""
Script to reset the alembic version table.
"""

import os
import sys
from sqlalchemy import create_engine, text

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import settings

def reset_alembic_version():
    """Reset the alembic version table."""
    try:
        # Create engine
        engine = create_engine(settings.DATABASE_URL)
        
        # Connect and reset the version table
        with engine.connect() as conn:
            # Drop and recreate the alembic_version table
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"))
            
            # Insert our new initial migration
            conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('001_initial_schema')"))
            
            conn.commit()
            print("✅ Successfully reset alembic version table")
            
    except Exception as e:
        print(f"❌ Error resetting alembic version: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if reset_alembic_version():
        print("🎉 Alembic version table reset successfully!")
    else:
        print("💥 Failed to reset alembic version table")
        sys.exit(1) 