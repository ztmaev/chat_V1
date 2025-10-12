#!/usr/bin/env python3
"""
Migration script to update users table schema to match new requirements
"""

import sqlite3
import sys
from datetime import datetime

def migrate_database(db_path="messaging.db"):
    """Migrate users table to new schema with firebase_uid"""
    
    print(f"🔄 Starting schema migration for {db_path}")
    print(f"⏰ Migration started at: {datetime.now().isoformat()}")
    print()
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check current users table schema
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='users'
        """)
        
        result = cursor.fetchone()
        if not result:
            print("❌ Users table does not exist")
            conn.close()
            return False
        
        current_schema = result[0]
        print("📋 Current users table schema:")
        print(current_schema)
        print()
        
        # Check if migration is needed
        if 'firebase_uid' in current_schema:
            print("✅ Users table already has correct schema - no migration needed")
            conn.close()
            return True
        
        print("🔄 Migration needed - updating schema...")
        print()
        
        # Get existing data
        cursor.execute("SELECT * FROM users")
        existing_users = cursor.fetchall()
        print(f"📊 Found {len(existing_users)} existing users to migrate")
        
        # Drop old users table
        print("🗑️  Dropping old users table...")
        cursor.execute("DROP TABLE IF EXISTS users")
        
        # Create new users table with correct schema
        print("📊 Creating new users table with firebase_uid...")
        cursor.execute('''
            CREATE TABLE users (
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
        
        print("✅ New users table created")
        
        # Migrate existing data if any
        if existing_users:
            print(f"🔄 Migrating {len(existing_users)} users to new schema...")
            for user in existing_users:
                try:
                    # Map old columns to new columns
                    cursor.execute('''
                        INSERT INTO users 
                        (firebase_uid, email, display_name, photo_url, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        user['id'],  # Old 'id' becomes 'firebase_uid'
                        user['email'],
                        user['display_name'],
                        user.get('avatar_url'),  # Old 'avatar_url' becomes 'photo_url'
                        user['created_at'],
                        user['updated_at']
                    ))
                    print(f"   ✅ Migrated user: {user['email']}")
                except Exception as e:
                    print(f"   ⚠️  Failed to migrate user {user.get('email', 'unknown')}: {e}")
        
        # Create index on email
        print("📊 Creating index on email field...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_users_email 
            ON users(email)
        ''')
        
        print("✅ Email index created")
        
        # Commit changes
        conn.commit()
        
        # Verify new schema
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='users'
        """)
        
        new_schema = cursor.fetchone()[0]
        print()
        print("📋 New users table schema:")
        print(new_schema)
        print()
        
        # Get statistics
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM threads")
        thread_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM conversations")
        conversation_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM messages")
        message_count = cursor.fetchone()[0]
        
        print("📊 Database Statistics After Migration:")
        print(f"   - Users: {user_count}")
        print(f"   - Threads: {thread_count}")
        print(f"   - Conversations: {conversation_count}")
        print(f"   - Messages: {message_count}")
        print()
        
        conn.close()
        
        print("✅ Schema migration completed successfully!")
        print(f"⏰ Migration finished at: {datetime.now().isoformat()}")
        print()
        print("⚠️  IMPORTANT: Restart the API server to use the new schema")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "messaging.db"
    
    print("=" * 70)
    print("   DATABASE MIGRATION: Update Users Table Schema")
    print("=" * 70)
    print()
    
    success = migrate_database(db_path)
    
    print()
    print("=" * 70)
    
    sys.exit(0 if success else 1)
