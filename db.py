import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import uuid


class MessagingDatabase:
    def __init__(self, db_path="messaging.db"):
        self.db_path = db_path
        self._create_tables()
        self._create_triggers()
    
    def get_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_tables(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Users table - stores user information from Firebase
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
            
            # Threads table - groups conversations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    description TEXT,
                    campaign_id TEXT,
                    created_by TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    UNIQUE(campaign_id, created_by)
                )
            ''')
            
            # Conversations table - can have 1 or 2 participants in a thread
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    name TEXT,
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
            
            # Messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    sender_type TEXT NOT NULL,
                    sender_name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    content TEXT,
                    text_content TEXT,
                    caption TEXT,
                    filename TEXT,
                    file_path TEXT,
                    file_size INTEGER,
                    has_attachment BOOLEAN DEFAULT FALSE,
                    attachments TEXT,
                    timestamp TEXT NOT NULL,
                    status TEXT DEFAULT 'sent',
                    deleted BOOLEAN DEFAULT FALSE,
                    deleted_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_users_email 
                ON users(email)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_conversations_thread 
                ON conversations(thread_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_conversations_participants 
                ON conversations(participant1_id, participant2_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_conversation 
                ON messages(conversation_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_thread 
                ON messages(thread_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
                ON messages(timestamp)
            ''')
            
            conn.commit()
        finally:
            conn.close()
    
    def _create_triggers(self):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Update conversation last_message when new message is inserted
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS update_conversation_on_message_insert
                AFTER INSERT ON messages
                WHEN NEW.deleted = FALSE
                BEGIN
                    UPDATE conversations
                    SET last_message = COALESCE(NEW.text_content, NEW.content, 'Attachment'),
                        last_message_time = NEW.timestamp,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = NEW.conversation_id;
                    
                    UPDATE threads
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = NEW.thread_id;
                END;
            ''')
            
            # Update conversation when message is deleted
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS update_conversation_on_message_delete
                AFTER UPDATE ON messages
                WHEN NEW.deleted = TRUE AND OLD.deleted = FALSE
                BEGIN
                    UPDATE conversations
                    SET last_message = 'Message was deleted',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = NEW.conversation_id;
                END;
            ''')
            
            conn.commit()
        finally:
            conn.close()
    
    # User operations
    def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[Dict]:
        """Get user by Firebase UID"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('SELECT * FROM users WHERE firebase_uid = ?', (firebase_uid,))
            row = cursor.fetchone()
            if row:
                user = dict(row)
                user['email_verified'] = bool(user.get('email_verified', False))
                return user
            return None
        finally:
            conn.close()
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('SELECT * FROM users WHERE email = ?', (email,))
            row = cursor.fetchone()
            if row:
                user = dict(row)
                user['email_verified'] = bool(user.get('email_verified', False))
                return user
            return None
        finally:
            conn.close()
    
    def create_or_update_user(self, user_data: Dict) -> str:
        """Create or update user from Firebase data"""
        firebase_uid = user_data.get('firebase_uid')
        if not firebase_uid:
            raise ValueError('firebase_uid is required')
        
        conn = self.get_connection()
        try:
            # Check if user exists
            existing_user = self.get_user_by_firebase_uid(firebase_uid)
            
            if existing_user:
                # Update existing user
                conn.execute('''
                    UPDATE users
                    SET email = ?,
                        display_name = ?,
                        photo_url = ?,
                        role = ?,
                        phone_number = ?,
                        email_verified = ?,
                        updated_at = CURRENT_TIMESTAMP,
                        last_seen = ?
                    WHERE firebase_uid = ?
                ''', (
                    user_data.get('email'),
                    user_data.get('display_name'),
                    user_data.get('photo_url'),
                    user_data.get('role'),
                    user_data.get('phone_number'),
                    user_data.get('email_verified', False),
                    datetime.now().isoformat() + 'Z',
                    firebase_uid
                ))
            else:
                # Create new user
                conn.execute('''
                    INSERT INTO users 
                    (firebase_uid, email, display_name, photo_url, role, phone_number, email_verified, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    firebase_uid,
                    user_data.get('email'),
                    user_data.get('display_name'),
                    user_data.get('photo_url'),
                    user_data.get('role'),
                    user_data.get('phone_number'),
                    user_data.get('email_verified', False),
                    datetime.now().isoformat() + 'Z'
                ))
            
            conn.commit()
            return firebase_uid
        finally:
            conn.close()
    
    def update_user_last_seen(self, firebase_uid: str) -> bool:
        """Update user's last seen timestamp"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                UPDATE users
                SET last_seen = ?
                WHERE firebase_uid = ?
            ''', (datetime.now().isoformat() + 'Z', firebase_uid))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get_all_users(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get all users with pagination"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT * FROM users
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            users = []
            for row in cursor.fetchall():
                user = dict(row)
                user['email_verified'] = bool(user.get('email_verified', False))
                users.append(user)
            return users
        finally:
            conn.close()
    
    def user_exists(self, firebase_uid: str) -> bool:
        """Check if user exists"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('SELECT 1 FROM users WHERE firebase_uid = ?', (firebase_uid,))
            return cursor.fetchone() is not None
        finally:
            conn.close()
    
    # Thread operations
    def get_threads(self) -> List[Dict]:
        """Get all threads"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT t.*,
                       COUNT(DISTINCT c.id) as conversation_count,
                       SUM(c.unread_count) as total_unread
                FROM threads t
                LEFT JOIN conversations c ON t.id = c.thread_id
                WHERE t.status = 'active'
                GROUP BY t.id
                ORDER BY t.updated_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_threads_for_user(self, user_id: str) -> List[Dict]:
        """Get threads where user is creator OR participant in any conversation"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT DISTINCT t.*,
                       COUNT(DISTINCT c.id) as conversation_count,
                       SUM(c.unread_count) as total_unread
                FROM threads t
                LEFT JOIN conversations c ON t.id = c.thread_id
                WHERE t.status = 'active'
                  AND (t.created_by = ? 
                       OR c.participant1_id = ? 
                       OR c.participant2_id = ?)
                GROUP BY t.id
                ORDER BY t.updated_at DESC
            ''', (user_id, user_id, user_id))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_thread_by_id(self, thread_id: str) -> Optional[Dict]:
        """Get thread by ID"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('SELECT * FROM threads WHERE id = ?', (thread_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def create_thread(self, thread_data: Dict) -> str:
        """Create a new thread (idempotent - returns existing if campaign_id + created_by match)"""
        thread_id = thread_data.get('id', f"t{uuid.uuid4().hex[:8]}")
        campaign_id = thread_data.get('campaign_id')
        created_by = thread_data.get('created_by', '')
        
        conn = self.get_connection()
        try:
            # Check if thread already exists for this campaign_id and user
            if campaign_id and created_by:
                cursor = conn.execute('''
                    SELECT id FROM threads 
                    WHERE campaign_id = ? AND created_by = ?
                ''', (campaign_id, created_by))
                existing = cursor.fetchone()
                if existing:
                    # Thread already exists, return existing ID
                    return existing['id']
            
            # Create new thread
            conn.execute('''
                INSERT INTO threads (id, title, description, campaign_id, created_by, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                thread_id,
                thread_data.get('title', 'New Thread'),
                thread_data.get('description', ''),
                campaign_id,
                created_by,
                thread_data.get('status', 'active')
            ))
            conn.commit()
            return thread_id
        except sqlite3.IntegrityError as e:
            # Handle UNIQUE constraint error (for databases with the constraint)
            if 'UNIQUE constraint failed' in str(e) and campaign_id and created_by:
                # Fetch existing thread
                cursor = conn.execute('''
                    SELECT id FROM threads 
                    WHERE campaign_id = ? AND created_by = ?
                ''', (campaign_id, created_by))
                existing = cursor.fetchone()
                if existing:
                    return existing['id']
            raise
        finally:
            conn.close()
    
    def thread_exists(self, thread_id: str) -> bool:
        """Check if thread exists"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('SELECT 1 FROM threads WHERE id = ?', (thread_id,))
            return cursor.fetchone() is not None
        finally:
            conn.close()
    
    def user_has_thread_access(self, thread_id: str, user_id: str) -> bool:
        """Check if user has access to thread (creator or participant in any conversation)"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT 1 FROM threads t
                LEFT JOIN conversations c ON t.id = c.thread_id
                WHERE t.id = ?
                  AND (t.created_by = ? 
                       OR c.participant1_id = ? 
                       OR c.participant2_id = ?)
                LIMIT 1
            ''', (thread_id, user_id, user_id, user_id))
            return cursor.fetchone() is not None
        finally:
            conn.close()
    
    # Conversation operations
    def get_conversations_by_thread(self, thread_id: str, user_id: str = None) -> List[Dict]:
        """Get all conversations in a thread, optionally filtered by user participation"""
        conn = self.get_connection()
        try:
            if user_id:
                # Only return conversations where the user is a participant
                cursor = conn.execute('''
                    SELECT * FROM conversations 
                    WHERE thread_id = ? AND status = 'active'
                    AND (participant1_id = ? OR participant2_id = ?)
                    ORDER BY updated_at DESC
                ''', (thread_id, user_id, user_id))
            else:
                # Return all conversations (admin use case)
                cursor = conn.execute('''
                    SELECT * FROM conversations 
                    WHERE thread_id = ? AND status = 'active'
                    ORDER BY updated_at DESC
                ''', (thread_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_conversation_by_id(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation by ID"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('SELECT * FROM conversations WHERE id = ?', (conversation_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def get_or_create_conversation(self, thread_id: str, participant1_id: str, participant2_id: str = None, 
                                   participant1_name: str = '', participant2_name: str = None,
                                   participant1_avatar: str = '', participant2_avatar: str = None,
                                   name: str = None) -> str:
        """
        Get existing conversation or create new one in a thread.
        participant2 is optional - conversation can be created with only participant1.
        """
        conn = self.get_connection()
        try:
            # If participant2 is specified, check if conversation exists between them
            if participant2_id:
                # Normalize participant order (smaller ID first) to ensure uniqueness
                p1_id, p2_id = participant1_id, participant2_id
                p1_name, p2_name = participant1_name, participant2_name
                p1_avatar, p2_avatar = participant1_avatar, participant2_avatar
                
                if p1_id > p2_id:
                    p1_id, p2_id = p2_id, p1_id
                    p1_name, p2_name = p2_name, p1_name
                    p1_avatar, p2_avatar = p2_avatar, p1_avatar
                
                cursor = conn.execute('''
                    SELECT id FROM conversations 
                    WHERE thread_id = ? AND participant1_id = ? AND participant2_id = ?
                ''', (thread_id, p1_id, p2_id))
                
                row = cursor.fetchone()
                if row:
                    return row['id']
                
                # Create new conversation with both participants
                conversation_id = f"c{uuid.uuid4().hex[:8]}"
                conn.execute('''
                    INSERT INTO conversations 
                    (id, thread_id, name, participant1_id, participant1_name, participant1_avatar,
                     participant2_id, participant2_name, participant2_avatar)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    conversation_id, thread_id, name,
                    p1_id, p1_name, p1_avatar,
                    p2_id, p2_name, p2_avatar
                ))
            else:
                # Create conversation with only participant1
                conversation_id = f"c{uuid.uuid4().hex[:8]}"
                conn.execute('''
                    INSERT INTO conversations 
                    (id, thread_id, name, participant1_id, participant1_name, participant1_avatar,
                     participant2_id, participant2_name, participant2_avatar)
                    VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL)
                ''', (
                    conversation_id, thread_id, name,
                    participant1_id, participant1_name, participant1_avatar
                ))
            
            conn.commit()
            return conversation_id
        finally:
            conn.close()
    
    def add_participant2_to_conversation(self, conversation_id: str, participant2_id: str,
                                        participant2_name: str, participant2_avatar: str = '') -> bool:
        """Add participant2 to an existing conversation that has only participant1"""
        conn = self.get_connection()
        try:
            conn.execute('''
                UPDATE conversations
                SET participant2_id = ?,
                    participant2_name = ?,
                    participant2_avatar = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND participant2_id IS NULL
            ''', (participant2_id, participant2_name, participant2_avatar, conversation_id))
            
            affected_rows = conn.total_changes
            conn.commit()
            return affected_rows > 0
        finally:
            conn.close()
    
    def conversation_exists(self, conversation_id: str) -> bool:
        """Check if conversation exists"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('SELECT 1 FROM conversations WHERE id = ?', (conversation_id,))
            return cursor.fetchone() is not None
        finally:
            conn.close()
    
    def update_conversation_read_status_detailed(self, conversation_id: str) -> Dict:
        """Mark conversation as read with detailed status information"""
        conn = self.get_connection()
        try:
            cursor = conn.execute(
                'SELECT unread_count FROM conversations WHERE id = ?',
                (conversation_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return {
                    'success': False,
                    'reason': 'conversation_not_found',
                    'message': 'Conversation not found',
                    'updated': False
                }
            
            current_unread_count = row[0]
            
            if current_unread_count > 0:
                conn.execute(
                    'UPDATE conversations SET unread_count = 0 WHERE id = ?',
                    (conversation_id,)
                )
                conn.commit()
                return {
                    'success': True,
                    'reason': 'marked_as_read',
                    'message': f'Conversation marked as read ({current_unread_count} unread messages cleared)',
                    'updated': True,
                    'cleared_unread_count': current_unread_count
                }
            else:
                return {
                    'success': True,
                    'reason': 'already_read',
                    'message': 'Conversation was already marked as read',
                    'updated': False
                }
        finally:
            conn.close()
    
    # Message operations
    def get_messages(self, conversation_id: str) -> List[Dict]:
        """Get all messages for a conversation"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT * FROM messages 
                WHERE conversation_id = ? 
                ORDER BY timestamp ASC
            ''', (conversation_id,))
            
            messages = []
            for row in cursor.fetchall():
                message = dict(row)
                message['deleted'] = bool(message['deleted'])
                message['has_attachment'] = bool(message.get('has_attachment', False))
                messages.append(message)
            
            return messages
        finally:
            conn.close()
    
    def get_messages_by_thread(self, thread_id: str) -> List[Dict]:
        """Get all messages in a thread"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT * FROM messages 
                WHERE thread_id = ? 
                ORDER BY timestamp ASC
            ''', (thread_id,))
            
            messages = []
            for row in cursor.fetchall():
                message = dict(row)
                message['deleted'] = bool(message['deleted'])
                message['has_attachment'] = bool(message.get('has_attachment', False))
                messages.append(message)
            
            return messages
        finally:
            conn.close()
    
    def create_message(self, message_data: Dict) -> str:
        """Create a new message"""
        message_id = message_data.get('id', f"m{uuid.uuid4().hex[:8]}")
        
        # Handle attachments
        import json
        attachments_json = None
        if message_data.get('attachments'):
            attachments_json = json.dumps(message_data['attachments'])
        
        conn = self.get_connection()
        try:
            conn.execute('''
                INSERT INTO messages 
                (id, conversation_id, thread_id, sender_id, sender_type, sender_name, type, 
                 content, text_content, caption, filename, file_size, has_attachment, attachments,
                 timestamp, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message_id,
                message_data['conversation_id'],
                message_data['thread_id'],
                message_data['sender_id'],
                message_data['sender_type'],
                message_data['sender_name'],
                message_data['type'],
                message_data.get('content', ''),
                message_data.get('text_content', message_data.get('content', '')),
                message_data.get('caption'),
                message_data.get('filename'),
                message_data.get('file_size'),
                message_data.get('has_attachment', False),
                attachments_json,
                message_data['timestamp'],
                message_data.get('status', 'delivered')
            ))
            conn.commit()
            return message_id
        finally:
            conn.close()
    
    def get_message_by_id(self, message_id: str) -> Optional[Dict]:
        """Get message by ID"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('SELECT * FROM messages WHERE id = ?', (message_id,))
            row = cursor.fetchone()
            if row:
                message = dict(row)
                message['deleted'] = bool(message['deleted'])
                message['has_attachment'] = bool(message.get('has_attachment', False))
                
                # Parse attachments JSON
                if message.get('attachments'):
                    import json
                    try:
                        message['attachments'] = json.loads(message['attachments'])
                    except:
                        message['attachments'] = []
                
                return message
            return None
        finally:
            conn.close()
    
    def delete_message(self, message_id: str) -> bool:
        """Mark a message as deleted"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                UPDATE messages 
                SET deleted = TRUE, 
                    deleted_at = ?, 
                    content = 'This message was deleted',
                    text_content = 'This message was deleted',
                    type = 'deleted'
                WHERE id = ?
            ''', (datetime.now().isoformat() + 'Z', message_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    # Statistics
    def get_stats(self) -> Dict:
        """Get messaging statistics"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT COUNT(*) as total_users
                FROM users
            ''')
            stats = dict(cursor.fetchone())
            
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_threads
                FROM threads
                WHERE status = 'active'
            ''')
            stats.update(dict(cursor.fetchone()))
            
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total_conversations,
                    SUM(unread_count) as total_unread
                FROM conversations
                WHERE status = 'active'
            ''')
            stats.update(dict(cursor.fetchone()))
            
            cursor = conn.execute('''
                SELECT COUNT(*) as total_messages
                FROM messages
                WHERE deleted = FALSE
            ''')
            stats.update(dict(cursor.fetchone()))
            
            return stats
        finally:
            conn.close()


# Global database instance
_db_instance = None

def get_db() -> MessagingDatabase:
    """Get global database instance (singleton pattern)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = MessagingDatabase()
    return _db_instance

def init_db(db_path: str = "messaging.db"):
    """Initialize database with custom path"""
    global _db_instance
    _db_instance = MessagingDatabase(db_path)
    return _db_instance
