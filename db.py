import sqlite3
from logger_config import logger
from datetime import datetime
from typing import List, Dict, Optional
import uuid


class MessagingDatabase:
    def __init__(self, db_path="messaging.db"):
        self.db_path = db_path
        self._create_tables()
        self._create_triggers()
        self._migrate_db()
    
    def _migrate_db(self):
        """Run database migrations to add missing columns"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Check for is_forwarded in messages table
            cursor.execute("PRAGMA table_info(messages)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'is_forwarded' not in columns:
                cursor.execute('ALTER TABLE messages ADD COLUMN is_forwarded BOOLEAN DEFAULT FALSE')
                logger.info("Added is_forwarded column to messages table")
                
            if 'original_message_id' not in columns:
                cursor.execute('ALTER TABLE messages ADD COLUMN original_message_id TEXT')
                logger.info("Added original_message_id column to messages table")
            
            # Check for participant2_email in conversations table
            cursor.execute("PRAGMA table_info(conversations)")
            conv_columns = [col[1] for col in cursor.fetchall()]
            
            if 'participant2_email' not in conv_columns:
                cursor.execute('ALTER TABLE conversations ADD COLUMN participant2_email TEXT')
                logger.info("Added participant2_email column to conversations table")
                
            if 'participant_type' not in conv_columns:
                cursor.execute('ALTER TABLE conversations ADD COLUMN participant_type TEXT')
                logger.info("Added participant_type column to conversations table")
                
            conn.commit()
        finally:
            conn.close()
    
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
                    UNIQUE(campaign_id)
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
                    participant2_email TEXT,
                    participant_type TEXT,
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
                    is_forwarded BOOLEAN DEFAULT FALSE,
                    original_message_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
                )
            ''')

            # Message read status table - tracks which users have read which messages
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS message_read_status (
                    message_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    read_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (message_id, user_id),
                    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
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
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_message_read_status_user
                ON message_read_status(user_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_message_read_status_message
                ON message_read_status(message_id)
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
        
        email = user_data.get('email')
        
        conn = self.get_connection()
        try:
            # Check if user exists by Firebase UID
            existing_user = self.get_user_by_firebase_uid(firebase_uid)
            
            # If user doesn't exist by UID but email is provided, check by email
            # This handles the case where Firebase account was deleted and recreated with new UID
            if not existing_user and email:
                existing_user_by_email = self.get_user_by_email(email)
                if existing_user_by_email:
                    logger.info(f"Found existing user by email {email} with different Firebase UID")
                    logger.info(f"Old UID: {existing_user_by_email.get('firebase_uid')}, New UID: {firebase_uid}")
                    logger.info("Updating record with new Firebase UID...")
                    # Update the existing record with the new Firebase UID
                    conn.execute('''
                        UPDATE users
                        SET firebase_uid = ?,
                            display_name = ?,
                            photo_url = ?,
                            role = ?,
                            phone_number = ?,
                            email_verified = ?,
                            updated_at = CURRENT_TIMESTAMP,
                            last_seen = ?
                        WHERE email = ?
                    ''', (
                        firebase_uid,
                        user_data.get('display_name'),
                        user_data.get('photo_url'),
                        user_data.get('role'),
                        user_data.get('phone_number'),
                        user_data.get('email_verified', False),
                        datetime.now().isoformat() + 'Z',
                        email
                    ))
                    conn.commit()
                    return firebase_uid
            
            if existing_user:
                # Update existing user (by Firebase UID)
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
                # Create new user (no existing record by UID or email)
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
    
    def get_threads_for_user(self, user_id: str, user_role: str = None) -> List[Dict]:
        """
        Get threads for user based on their role:
        - Admins (main_admin, billing_admin, campaign_admin): See all threads with at least one conversation
        - Others: See threads where they are creator OR participant in any conversation
        """
        conn = self.get_connection()
        try:
            # Check if user is an admin
            is_admin = user_role in ['main_admin', 'billing_admin', 'campaign_admin']
            
            if is_admin:
                # Admins see all threads that have at least one conversation
                cursor = conn.execute('''
                    SELECT DISTINCT t.*,
                           COUNT(DISTINCT c.id) as conversation_count,
                           SUM(c.unread_count) as total_unread
                    FROM threads t
                    LEFT JOIN conversations c ON t.id = c.thread_id
                    WHERE t.status = 'active'
                    GROUP BY t.id
                    HAVING COUNT(DISTINCT c.id) > 0
                    ORDER BY t.updated_at DESC
                ''')
            else:
                # Non-admins see only their own threads
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
        """
        Create a new thread (idempotent - returns existing if campaign_id + created_by match)
        
        For redundancy, when campaign_id is provided, it is used as the thread_id.
        This ensures thread IDs are predictable and tied directly to campaigns.
        """
        campaign_id = thread_data.get('campaign_id')
        created_by = thread_data.get('created_by', '')
        
        # Use campaign_id as thread_id for redundancy when available
        # Otherwise fall back to provided id or generate a new one
        if campaign_id:
            thread_id = campaign_id
        else:
            thread_id = thread_data.get('id', f"t{uuid.uuid4().hex[:8]}")
        
        conn = self.get_connection()
        try:
            # Check if thread already exists for this campaign_id
            if campaign_id:
                cursor = conn.execute('''
                    SELECT id, created_by FROM threads 
                    WHERE campaign_id = ?
                ''', (campaign_id,))
                existing = cursor.fetchone()
                if existing:
                    # Thread exists. Check if we need to update the owner.
                    # This happens if it was created with a placeholder or by the wrong person.
                    # We only update if the new created_by is NOT a placeholder, 
                    # OR if the existing creator IS a placeholder.
                    existing_creator = existing['created_by']
                    if created_by and existing_creator != created_by:
                        is_existing_placeholder = existing_creator.startswith('placeholder_')
                        is_new_placeholder = created_by.startswith('placeholder_')
                        
                        if is_existing_placeholder and not is_new_placeholder:
                            logger.info(f"Updating thread {existing['id']} owner from placeholder {existing_creator} to actual UID {created_by}")
                            conn.execute('UPDATE threads SET created_by = ? WHERE id = ?', (created_by, existing['id']))
                            conn.commit()
                    
                    return existing['id']
            
            # Check if a thread with this ID already exists (important when using campaign_id as thread_id)
            cursor = conn.execute('SELECT id, created_by FROM threads WHERE id = ?', (thread_id,))
            existing_by_id = cursor.fetchone()
            if existing_by_id:
                # Thread exists. Check ownership update as well.
                existing_creator = existing_by_id['created_by']
                if created_by and existing_creator != created_by:
                    is_existing_placeholder = existing_creator.startswith('placeholder_')
                    is_new_placeholder = created_by.startswith('placeholder_')
                    
                    if is_existing_placeholder and not is_new_placeholder:
                        logger.info(f"Updating thread {thread_id} owner from placeholder {existing_creator} to actual UID {created_by}")
                        conn.execute('UPDATE threads SET created_by = ? WHERE id = ?', (created_by, thread_id))
                        conn.commit()

                return existing_by_id['id']
            
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
            # Handle UNIQUE constraint error
            if 'UNIQUE constraint failed' in str(e):
                if 'threads.id' in str(e):
                    cursor = conn.execute('SELECT id FROM threads WHERE id = ?', (thread_id,))
                elif 'threads.campaign_id' in str(e):
                    cursor = conn.execute('SELECT id FROM threads WHERE campaign_id = ?', (campaign_id,))
                else:
                    return thread_id # Fallback
                
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
    
    def user_has_thread_access(self, thread_id: str, user_id: str, user_role: str = None) -> bool:
        """
        Check if user has access to thread:
        - Admins: Have access to all threads
        - Others: Access only if creator or participant in any conversation
        """
        conn = self.get_connection()
        try:
            # Check if user is an admin
            is_admin = user_role in ['main_admin', 'billing_admin', 'campaign_admin']
            
            if is_admin:
                # Admins have access to all threads
                cursor = conn.execute('SELECT 1 FROM threads WHERE id = ? LIMIT 1', (thread_id,))
            else:
                # Non-admins need to be creator or participant
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
            conversations = [dict(row) for row in cursor.fetchall()]

            # Enrich with participant roles/emails for UI correctness.
            # These fields are not stored on the conversation row, but are needed by the
            # admin UI to correctly label participants (client vs influencer) especially
            # for single-participant conversations created by a client.
            for conv in conversations:
                p1_id = conv.get('participant1_id')
                p2_id = conv.get('participant2_id')

                if p1_id:
                    p1_user = self.get_user_by_firebase_uid(p1_id)
                    if p1_user:
                        conv['participant1_email'] = p1_user.get('email')
                        conv['participant1_role'] = p1_user.get('role')

                if p2_id:
                    p2_user = self.get_user_by_firebase_uid(p2_id)
                    if p2_user:
                        conv['participant2_role'] = p2_user.get('role')
                        # If participant2_email is missing but exists on user, expose it
                        # (helps admin UI matching for portal users).
                        if not conv.get('participant2_email') and p2_user.get('email'):
                            conv['participant2_email'] = p2_user.get('email')

            return conversations
        finally:
            conn.close()
    
    def get_conversation_by_id(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation by ID"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('SELECT * FROM conversations WHERE id = ?', (conversation_id,))
            row = cursor.fetchone()
            if not row:
                return None

            conv = dict(row)

            # Enrich with participant roles/emails (see get_conversations_by_thread).
            p1_id = conv.get('participant1_id')
            p2_id = conv.get('participant2_id')

            if p1_id:
                p1_user = self.get_user_by_firebase_uid(p1_id)
                if p1_user:
                    conv['participant1_email'] = p1_user.get('email')
                    conv['participant1_role'] = p1_user.get('role')

            if p2_id:
                p2_user = self.get_user_by_firebase_uid(p2_id)
                if p2_user:
                    conv['participant2_role'] = p2_user.get('role')
                    if not conv.get('participant2_email') and p2_user.get('email'):
                        conv['participant2_email'] = p2_user.get('email')

            return conv
        finally:
            conn.close()
    
    def get_or_create_conversation(self, thread_id: str, participant1_id: str, participant2_id: str = None, 
                                   participant1_name: str = '', participant2_name: str = None,
                                   participant1_avatar: str = '', participant2_avatar: str = None,
                                   participant2_email: str = None, participant_type: str = None,
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
                     participant2_id, participant2_name, participant2_avatar, participant2_email, participant_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    conversation_id, thread_id, name,
                    p1_id, p1_name, p1_avatar,
                    p2_id, p2_name, p2_avatar, participant2_email, participant_type
                ))
            else:
                # Create conversation with only participant1
                conversation_id = f"c{uuid.uuid4().hex[:8]}"
                conn.execute('''
                    INSERT INTO conversations 
                    (id, thread_id, name, participant1_id, participant1_name, participant1_avatar,
                     participant2_id, participant2_name, participant2_avatar, participant2_email, participant_type)
                    VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL)
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

    def get_unread_count_for_user(self, conversation_id: str, user_id: str) -> int:
        """Get the number of unread messages for a specific user in a conversation"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT COUNT(*) as unread_count
                FROM messages m
                WHERE m.conversation_id = ?
                  AND m.sender_id != ?
                  AND m.deleted = FALSE
                  AND m.id NOT IN (
                      SELECT message_id FROM message_read_status WHERE user_id = ?
                  )
            ''', (conversation_id, user_id, user_id))
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def get_thread_unread_count_for_user(self, thread_id: str, user_id: str) -> int:
        """Get the total number of unread messages for a specific user in a thread"""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT COUNT(*) as unread_count
                FROM messages m
                INNER JOIN conversations c ON m.conversation_id = c.id
                WHERE c.thread_id = ?
                  AND m.sender_id != ?
                  AND m.deleted = FALSE
                  AND (c.participant1_id = ? OR c.participant2_id = ?)
                  AND m.id NOT IN (
                      SELECT message_id FROM message_read_status WHERE user_id = ?
                  )
            ''', (thread_id, user_id, user_id, user_id, user_id))
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def mark_messages_as_read(self, conversation_id: str, user_id: str) -> Dict:
        """Mark all messages in a conversation as read for a specific user"""
        conn = self.get_connection()
        try:
            # Get all unread messages for this user in the conversation
            cursor = conn.execute('''
                SELECT m.id
                FROM messages m
                WHERE m.conversation_id = ?
                  AND m.sender_id != ?
                  AND m.deleted = FALSE
                  AND m.id NOT IN (
                      SELECT message_id FROM message_read_status WHERE user_id = ?
                  )
            ''', (conversation_id, user_id, user_id))

            unread_messages = [row[0] for row in cursor.fetchall()]

            if not unread_messages:
                return {
                    'success': True,
                    'reason': 'already_read',
                    'message': 'All messages already read',
                    'marked_count': 0
                }

            # Mark each message as read
            for message_id in unread_messages:
                conn.execute('''
                    INSERT OR IGNORE INTO message_read_status (message_id, user_id)
                    VALUES (?, ?)
                ''', (message_id, user_id))

            conn.commit()

            return {
                'success': True,
                'reason': 'marked_as_read',
                'message': f'{len(unread_messages)} messages marked as read',
                'marked_count': len(unread_messages)
            }
        finally:
            conn.close()

    # Message operations
    def get_messages(self, conversation_id: str) -> List[Dict]:
        """Get all messages for a conversation"""
        import json
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
                message['is_forwarded'] = bool(message.get('is_forwarded', False))
                message['original_message_id'] = message.get('original_message_id')
                
                # Parse attachments JSON if present
                if message.get('attachments'):
                    try:
                        message['attachments'] = json.loads(message['attachments'])
                    except (json.JSONDecodeError, TypeError):
                        message['attachments'] = []
                
                messages.append(message)
            
            return messages
        finally:
            conn.close()
    
    def get_messages_by_thread(self, thread_id: str) -> List[Dict]:
        """Get all messages in a thread"""
        import json
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
                message['is_forwarded'] = bool(message.get('is_forwarded', False))
                message['original_message_id'] = message.get('original_message_id')
                
                # Parse attachments JSON if present
                if message.get('attachments'):
                    try:
                        message['attachments'] = json.loads(message['attachments'])
                    except (json.JSONDecodeError, TypeError):
                        message['attachments'] = []
                
                messages.append(message)
            
            return messages
        finally:
            conn.close()
    
    def get_last_message(self, conversation_id: str) -> Optional[Dict]:
        """Get the last message in a conversation"""
        import json
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT * FROM messages 
                WHERE conversation_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (conversation_id,))
            
            row = cursor.fetchone()
            if row:
                message = dict(row)
                message['deleted'] = bool(message['deleted'])
                message['has_attachment'] = bool(message.get('has_attachment', False))
                message['is_forwarded'] = bool(message.get('is_forwarded', False))
                message['original_message_id'] = message.get('original_message_id')
                
                # Parse attachments JSON if present
                if message.get('attachments'):
                    try:
                        message['attachments'] = json.loads(message['attachments'])
                    except (json.JSONDecodeError, TypeError):
                        message['attachments'] = []
                
                return message
            return None
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
                 timestamp, status, is_forwarded, original_message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                message_data.get('status', 'delivered'),
                message_data.get('is_forwarded', False),
                message_data.get('original_message_id')
            ))
            conn.commit()
            return message_id
        finally:
            conn.close()
    
    def forward_message(self, original_message_id: str, target_conversation_id: str, target_thread_id: str, sender_id: str, sender_name: str, sender_type: str) -> Optional[str]:
        """Forward an existing message to another conversation"""
        message = self.get_message_by_id(original_message_id)
        if not message:
            return None
        
        # Prepare data for the new forwarded message
        new_message_id = f"m{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat() + 'Z'
        
        # Reuse fields from original message but update sender and target
        forward_data = {
            'id': new_message_id,
            'conversation_id': target_conversation_id,
            'thread_id': target_thread_id,
            'sender_id': sender_id,
            'sender_name': sender_name,
            'sender_type': sender_type,
            'type': message['type'],
            'content': message['content'],
            'text_content': message.get('text_content'),
            'caption': message.get('caption'),
            'filename': message.get('filename'),
            'file_size': message.get('file_size'),
            'has_attachment': message.get('has_attachment', False),
            'attachments': message.get('attachments'),
            'timestamp': timestamp,
            'status': 'sent',
            'is_forwarded': True,
            'original_message_id': original_message_id
        }
        
        return self.create_message(forward_data)

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
                message['is_forwarded'] = bool(message.get('is_forwarded', False))
                message['original_message_id'] = message.get('original_message_id')
                
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
                    COALESCE(SUM(unread_count), 0) as unread_messages
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
            
            cursor = conn.execute('''
                SELECT COUNT(DISTINCT id) as messages_with_attachments
                FROM messages
                WHERE deleted = FALSE
                AND has_attachment = TRUE
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
