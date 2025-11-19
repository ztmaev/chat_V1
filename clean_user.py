#!/usr/bin/env python3
"""
Script to clean/reset a user from the messaging database.
This resolves UNIQUE constraint errors when a user's Firebase UID changes.

Usage:
    python clean_user.py superadmin@hyptrb.africa
"""

import sqlite3
import sys
from datetime import datetime

DB_PATH = "messaging.db"

def clean_user(email):
    """
    Delete a user from the messaging database by email.
    This also cascades to their threads, conversations, and messages.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # First, check if user exists
        cursor.execute('SELECT firebase_uid, email, display_name, role FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ User not found: {email}")
            return False
        
        print(f"\n📋 Found user:")
        print(f"   Firebase UID: {user['firebase_uid']}")
        print(f"   Email: {user['email']}")
        print(f"   Display Name: {user['display_name']}")
        print(f"   Role: {user['role']}")
        
        # Count related data
        cursor.execute('SELECT COUNT(*) as count FROM threads WHERE created_by = ?', (user['firebase_uid'],))
        thread_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM conversations WHERE participant1_id = ? OR participant2_id = ?', 
                      (user['firebase_uid'], user['firebase_uid']))
        conv_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM messages WHERE sender_id = ?', (user['firebase_uid'],))
        msg_count = cursor.fetchone()['count']
        
        print(f"\n📊 Related data:")
        print(f"   Threads: {thread_count}")
        print(f"   Conversations: {conv_count}")
        print(f"   Messages: {msg_count}")
        
        # Confirm deletion
        response = input(f"\n⚠️  Delete user '{email}' and all related data? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Deletion cancelled")
            return False
        
        # Delete user (cascades will handle threads, conversations, messages)
        cursor.execute('DELETE FROM users WHERE email = ?', (email,))
        conn.commit()
        
        print(f"\n✅ Successfully deleted user: {email}")
        print(f"   - User record deleted")
        print(f"   - {thread_count} threads deleted (cascaded)")
        print(f"   - {conv_count} conversations deleted (cascaded)")
        print(f"   - {msg_count} messages deleted (cascaded)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def list_users():
    """List all users in the database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT firebase_uid, email, display_name, role, last_seen FROM users ORDER BY email')
        users = cursor.fetchall()
        
        if not users:
            print("📭 No users found in database")
            return
        
        print(f"\n👥 Users in database ({len(users)}):")
        print("-" * 80)
        for user in users:
            print(f"Email: {user['email']}")
            print(f"  Firebase UID: {user['firebase_uid']}")
            print(f"  Display Name: {user['display_name']}")
            print(f"  Role: {user['role']}")
            print(f"  Last Seen: {user['last_seen']}")
            print("-" * 80)
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 80)
    print("🗑️  Messaging Database User Cleanup Tool")
    print("=" * 80)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python clean_user.py <email>              # Delete a specific user")
        print("  python clean_user.py --list               # List all users")
        print("\nExample:")
        print("  python clean_user.py superadmin@hyptrb.africa")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        list_users()
    else:
        email = sys.argv[1]
        clean_user(email)

