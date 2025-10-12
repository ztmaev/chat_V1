#!/usr/bin/env python3
"""
Migration script to add 'name' column to conversations table.
This allows conversations to have custom names like "<Campaign Name> Discussion".
"""

import sqlite3
import sys
from pathlib import Path

def migrate_database(db_path="messaging.db"):
    """Add name column to conversations table"""
    
    print(f"🔄 Starting migration for {db_path}...")
    
    # Check if database exists
    if not Path(db_path).exists():
        print(f"❌ Database file not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if name column already exists
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'name' in columns:
            print("✅ Column 'name' already exists in conversations table")
            return True
        
        # Add name column
        print("📝 Adding 'name' column to conversations table...")
        cursor.execute("""
            ALTER TABLE conversations 
            ADD COLUMN name TEXT
        """)
        
        conn.commit()
        print("✅ Successfully added 'name' column to conversations table")
        
        # Verify the change
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'name' in columns:
            print("✅ Migration verified successfully")
            print(f"📊 Conversations table now has {len(columns)} columns")
            return True
        else:
            print("❌ Migration verification failed")
            return False
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "messaging.db"
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)
