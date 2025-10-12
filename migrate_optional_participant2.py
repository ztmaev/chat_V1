#!/usr/bin/env python3
"""
Migration script to make participant2 fields optional in conversations table
This allows conversations to be created without a second participant
"""

import sqlite3
import os

DB_PATH = 'messaging.db'

def migrate():
    """Make participant2 fields nullable in conversations table"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file {DB_PATH} not found")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        print("🔄 Starting migration: Make participant2 optional in conversations...")
        
        # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
        # Step 1: Create new table with nullable participant2 fields
        print("  📝 Creating new conversations table structure...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations_new (
                id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                participant1_id TEXT NOT NULL,
                participant1_name TEXT NOT NULL,
                participant1_avatar TEXT,
                participant2_id TEXT,
                participant2_name TEXT,
                participant2_avatar TEXT,
                last_message TEXT,
                last_message_time TEXT,
                unread_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
            )
        ''')
        
        # Step 2: Copy data from old table to new table
        print("  📋 Copying existing conversations...")
        cursor.execute('''
            INSERT INTO conversations_new 
            SELECT * FROM conversations
        ''')
        
        # Step 3: Drop triggers that reference conversations table
        print("  🗑️  Dropping triggers...")
        cursor.execute('DROP TRIGGER IF EXISTS update_conversation_on_message_insert')
        cursor.execute('DROP TRIGGER IF EXISTS update_conversation_on_message_update')
        cursor.execute('DROP TRIGGER IF EXISTS update_conversation_on_message_delete')
        
        # Step 4: Drop old table
        print("  🗑️  Removing old table...")
        cursor.execute('DROP TABLE conversations')
        
        # Step 5: Rename new table to original name
        print("  ✏️  Renaming new table...")
        cursor.execute('ALTER TABLE conversations_new RENAME TO conversations')
        
        # Step 6: Recreate triggers
        print("  🔧 Recreating triggers...")
        cursor.execute('''
            CREATE TRIGGER update_conversation_on_message_insert
            AFTER INSERT ON messages
            BEGIN
                UPDATE conversations
                SET last_message = NEW.content,
                    last_message_time = NEW.timestamp,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.conversation_id;
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER update_conversation_on_message_delete
            AFTER UPDATE OF deleted ON messages
            WHEN NEW.deleted = 1
            BEGIN
                UPDATE conversations
                SET last_message = '🗑️ This message was deleted',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.conversation_id 
                AND last_message_time = NEW.timestamp;
            END
        ''')
        
        # Step 7: Recreate indexes
        print("  📊 Creating indexes...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conversations_thread 
            ON conversations(thread_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conversations_participant1 
            ON conversations(participant1_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conversations_participant2 
            ON conversations(participant2_id)
        ''')
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # Show current conversations
        cursor.execute("SELECT id, thread_id, participant1_name, participant2_name FROM conversations")
        conversations = cursor.fetchall()
        print(f"\n📊 Current conversations in database: {len(conversations)}")
        for conv in conversations:
            p2_name = conv['participant2_name'] or '(no participant2)'
            print(f"  - {conv['id']}: {conv['participant1_name']} ↔ {p2_name}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
