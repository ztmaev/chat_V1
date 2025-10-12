#!/usr/bin/env python3
"""
Database Setup Script - Initialize database and populate with demo data

⚠️  WARNING: This script DELETES the existing database!
Use this for development/testing only.

Usage:
    python3 setup_demo_data.py

What it does:
    1. Removes existing messaging.db (if exists)
    2. Creates fresh database with schema
    3. Populates with demo threads, conversations, and messages
"""
import os
import sys
from db import get_db
from demodata import messaging_data

def setup_demo_database():
    """Initialize database and populate with demo data"""
    
    # Remove old database if exists
    db_path = "messaging.db"
    if os.path.exists(db_path):
        print(f"⚠️  Removing existing database: {db_path}")
        os.remove(db_path)
    
    # Initialize new database
    print("📦 Initializing new database with schema...")
    db = get_db()
    
    # Populate threads
    print("\n=== Creating Demo Threads ===")
    for thread in messaging_data['threads']:
        thread_id = db.create_thread(thread)
        print(f"✓ Created thread: {thread_id} - {thread['title']}")
    
    # Populate conversations
    print("\n=== Creating Demo Conversations ===")
    for conv in messaging_data['conversations']:
        conversation_id = db.get_or_create_conversation(
            thread_id=conv['thread_id'],
            participant1_id=conv['participant1_id'],
            participant2_id=conv['participant2_id'],
            participant1_name=conv['participant1_name'],
            participant2_name=conv['participant2_name'],
            participant1_avatar=conv.get('participant1_avatar', ''),
            participant2_avatar=conv.get('participant2_avatar', '')
        )
        print(f"✓ Created conversation: {conversation_id} between {conv['participant1_name']} and {conv['participant2_name']}")
    
    # Populate messages
    print("\n=== Creating Demo Messages ===")
    for msg in messaging_data['messages']:
        message_id = db.create_message(msg)
        print(f"✓ Created message: {message_id} in conversation {msg['conversation_id']}")
    
    # Display statistics
    print("\n=== Database Statistics ===")
    stats = db.get_stats()
    print(f"Total threads: {stats.get('total_threads', 0)}")
    print(f"Total conversations: {stats.get('total_conversations', 0)}")
    print(f"Total messages: {stats.get('total_messages', 0)}")
    print(f"Total unread: {stats.get('total_unread', 0)}")
    
    print("\n✅ Demo database setup completed successfully!")
    print("🚀 You can now start the API with: python3 app.py")

if __name__ == '__main__':
    try:
        setup_demo_database()
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)
