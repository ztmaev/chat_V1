#!/usr/bin/env python3
"""
Migration script to add users table to existing messaging database
"""

import sqlite3
import sys
from datetime import datetime

def migrate_database(db_path="messaging.db"):
    """Add users table to existing database"""
    
    print(f"🔄 Starting migration for {db_path}")
    print(f"⏰ Migration started at: {datetime.now().isoformat()}")
    print()
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if users table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='users'
        """)
        
        if cursor.fetchone():
            print("✅ Users table already exists - no migration needed")
            conn.close()
            return True
        
        print("📊 Creating users table...")
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                firebase_uid TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                display_name TEXT,
                photo_url TEXT,
                role TEXT,
                phone_number TEXT,
                email_verified BOOLEAN DEFAULT FALSE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen TEXT
            )
        ''')
        
        print("✅ Users table created successfully")
        
        # Create index on email
        print("📊 Creating index on email field...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_users_email 
            ON users(email)
        ''')
        
        print("✅ Email index created successfully")
        
        # Commit changes
        conn.commit()
        
        # Verify table was created
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='users'
        """)
        
        table_sql = cursor.fetchone()
        if table_sql:
            print()
            print("📋 Users table schema:")
            print(table_sql[0])
            print()
        
        # Get current database statistics
        cursor.execute("SELECT COUNT(*) FROM threads")
        thread_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM conversations")
        conversation_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM messages")
        message_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        print("📊 Database Statistics:")
        print(f"   - Threads: {thread_count}")
        print(f"   - Conversations: {conversation_count}")
        print(f"   - Messages: {message_count}")
        print(f"   - Users: {user_count}")
        print()
        
        conn.close()
        
        print("✅ Migration completed successfully!")
        print(f"⏰ Migration finished at: {datetime.now().isoformat()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "messaging.db"
    
    print("=" * 60)
    print("   DATABASE MIGRATION: Add Users Table")
    print("=" * 60)
    print()
    
    success = migrate_database(db_path)
    
    print()
    print("=" * 60)
    
    sys.exit(0 if success else 1)
