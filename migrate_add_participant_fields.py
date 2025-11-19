#!/usr/bin/env python3
"""
Migration script to add participant2_email and participant_type columns to conversations table.
This script is idempotent - it can be run multiple times safely.
"""

import sqlite3
import sys

def migrate_database(db_path='messaging.db'):
    """Add participant2_email and participant_type columns if they don't exist"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Add participant2_email column if it doesn't exist
        if 'participant2_email' not in columns:
            print("Adding participant2_email column...")
            cursor.execute('''
                ALTER TABLE conversations 
                ADD COLUMN participant2_email TEXT
            ''')
            print("✓ participant2_email column added")
        else:
            print("✓ participant2_email column already exists")
        
        # Add participant_type column if it doesn't exist
        if 'participant_type' not in columns:
            print("Adding participant_type column...")
            cursor.execute('''
                ALTER TABLE conversations 
                ADD COLUMN participant_type TEXT
            ''')
            print("✓ participant_type column added")
        else:
            print("✓ participant_type column already exists")
        
        conn.commit()
        print("\nMigration completed successfully!")
        
        # Show some stats
        cursor.execute("SELECT COUNT(*) FROM conversations")
        total_conversations = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM conversations WHERE participant_type IS NOT NULL")
        conversations_with_type = cursor.fetchone()[0]
        
        print(f"\nStatistics:")
        print(f"  Total conversations: {total_conversations}")
        print(f"  Conversations with participant_type set: {conversations_with_type}")
        print(f"  Conversations needing type inference: {total_conversations - conversations_with_type}")
        
        return True
        
    except Exception as e:
        print(f"Error during migration: {e}", file=sys.stderr)
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'messaging.db'
    print(f"Migrating database: {db_path}\n")
    
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)

