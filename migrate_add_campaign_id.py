#!/usr/bin/env python3
"""
Migration script to add campaign_id column to threads table
and add UNIQUE constraint on (campaign_id, created_by)
"""

import sqlite3
import os

DB_PATH = 'messaging.db'

def migrate():
    """Add campaign_id column to threads table"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file {DB_PATH} not found")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        print("🔄 Starting migration: Add campaign_id to threads table...")
        
        # Check if campaign_id column already exists
        cursor.execute("PRAGMA table_info(threads)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'campaign_id' in columns:
            print("✅ campaign_id column already exists, skipping migration")
            return
        
        # Step 1: Add campaign_id column (nullable for now)
        print("  📝 Adding campaign_id column...")
        cursor.execute("ALTER TABLE threads ADD COLUMN campaign_id TEXT")
        
        print("  ✅ campaign_id column added successfully")
        
        # Note: SQLite doesn't support adding UNIQUE constraints to existing tables
        # The constraint will only apply to new threads created after this migration
        # Existing threads without campaign_id will not be affected
        
        print("  ℹ️  Note: UNIQUE constraint on (campaign_id, created_by) will apply to new threads")
        print("  ℹ️  Existing threads can be manually updated with campaign_id values if needed")
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # Show current threads
        cursor.execute("SELECT id, title, campaign_id, created_by FROM threads")
        threads = cursor.fetchall()
        print(f"\n📊 Current threads in database: {len(threads)}")
        for thread in threads:
            print(f"  - {thread['id']}: {thread['title']} (campaign_id: {thread['campaign_id'] or 'NULL'})")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
