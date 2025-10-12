from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from db import get_db
import json
from firebase_auth import initialize_firebase, require_auth, optional_auth, get_current_user
from hyptrb_api import (
    fetch_user_role, 
    fetch_user_profile_by_role, 
    extract_display_name,
    fetch_client_campaigns,
    fetch_influencer_collaborations,
    HyptrbAPIError
)

# Try to import PIL and OpenCV for dimension extraction
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

app = Flask(__name__)
CORS(app)

# Initialize Firebase Admin SDK
try:
    initialize_firebase()
except Exception as e:
    print(f"⚠️  Warning: Firebase initialization failed: {e}")
    print("   API will continue but authentication will not work")

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'mp4', 'mov', 'avi'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize database
db = get_db()

def sync_user_campaign_threads(firebase_uid: str, email: str, role: str) -> int:
    """
    Sync user's threads with their Hyptrb campaigns.
    Creates missing threads for any campaigns not yet tracked.
    
    Args:
        firebase_uid: User's Firebase UID
        email: User's email
        role: User's role (client, influencer, admin)
    
    Returns:
        Number of threads created/synced
    """
    if role not in ['client', 'influencer']:
        return 0
    
    threads_created = 0
    
    try:
        if role == 'client':
            # Fetch client campaigns
            campaigns = fetch_client_campaigns(email)
            print(f"🔄 Syncing {len(campaigns)} campaigns for client {email}")
            
            # Create thread for each campaign
            for campaign in campaigns:
                campaign_id = campaign.get('_id')
                campaign_name = campaign.get('campaignName', 'Unnamed Campaign')
                
                if campaign_id:
                    thread_data = {
                        'title': campaign_name,
                        'description': f"Messages for campaign {campaign_name}",
                        'campaign_id': campaign_id,
                        'created_by': firebase_uid,
                        'status': 'active'
                    }
                    try:
                        thread_id = db.create_thread(thread_data)
                        threads_created += 1
                        print(f"  ✅ Thread synced: {thread_id} for campaign {campaign_name}")
                    except Exception as e:
                        print(f"  ⚠️  Failed to create thread for campaign {campaign_name}: {e}")
        
        elif role == 'influencer':
            # Fetch influencer collaborations
            collaborations = fetch_influencer_collaborations(firebase_uid)
            current_clients = collaborations.get('current_clients', [])
            
            # Count total campaigns
            total_campaigns = sum(len(client.get('campaigns', [])) for client in current_clients)
            print(f"🔄 Syncing {total_campaigns} campaigns for influencer {firebase_uid}")
            
            # Create thread for each campaign in current collaborations
            for client in current_clients:
                campaigns = client.get('campaigns', [])
                for campaign in campaigns:
                    campaign_id = campaign.get('campaign_id')
                    campaign_name = campaign.get('campaign_name', 'Unnamed Campaign')
                    
                    if campaign_id:
                        thread_data = {
                            'title': campaign_name,
                            'description': f"Messages for campaign {campaign_name}",
                            'campaign_id': campaign_id,
                            'created_by': firebase_uid,
                            'status': 'active'
                        }
                        try:
                            thread_id = db.create_thread(thread_data)
                            threads_created += 1
                            print(f"  ✅ Thread synced: {thread_id} for campaign {campaign_name}")
                        except Exception as e:
                            print(f"  ⚠️  Failed to create thread for campaign {campaign_name}: {e}")
    
    except HyptrbAPIError as e:
        print(f"⚠️  Warning: Failed to fetch campaigns for {email}: {e}")
    except Exception as e:
        print(f"⚠️  Warning: Error syncing threads for {email}: {e}")
    
    return threads_created

def ensure_user_exists(user_info: dict) -> dict:
    """
    Ensure user exists in database, create/update if needed.
    Fetches user role and profile from Hyptrb API on first access.
    """
    firebase_uid = user_info['uid']
    email = user_info.get('email')
    
    # Check if user already exists in database
    existing_user = db.get_user_by_firebase_uid(firebase_uid)
    
    # If user doesn't exist or doesn't have role, fetch from Hyptrb API
    if not existing_user or not existing_user.get('role'):
        display_name = user_info.get('name') or email.split('@')[0] if email else 'Unknown User'
        role = None
        photo_url = user_info.get('picture')
        phone_number = user_info.get('phone_number')
        
        try:
            # Step 1: Fetch user role from Hyptrb API
            if email:
                role_data = fetch_user_role(email)
                if role_data:
                    role = role_data.get('role')
                    
                    # Step 2: Fetch profile based on role
                    if role:
                        try:
                            # For influencer, we need the influencer_uid
                            influencer_uid = firebase_uid if role == 'influencer' else None
                            profile_data = fetch_user_profile_by_role(email, role, influencer_uid)
                            
                            if profile_data:
                                # Step 3: Extract display name from profile
                                display_name = extract_display_name(profile_data, role)
                                
                                # Extract additional info based on role
                                if role == 'influencer':
                                    photo_url = profile_data.get('profile_picture_url') or photo_url
                                    phone_number = profile_data.get('contact_phone') or phone_number
                                elif role == 'client':
                                    # Clients might not have profile pictures in the API
                                    pass
                                elif role == 'admin':
                                    photo_url = profile_data.get('photo_url') or photo_url
                                    phone_number = profile_data.get('phone_number') or phone_number
                        except HyptrbAPIError as e:
                            print(f"⚠️  Warning: Failed to fetch profile for {email}: {e}")
                            # Continue with basic info even if profile fetch fails
        except HyptrbAPIError as e:
            print(f"⚠️  Warning: Failed to fetch role for {email}: {e}")
            # Continue with basic info even if role fetch fails
    
        # Create/update user with fetched information
        user_data = {
            'firebase_uid': firebase_uid,
            'email': email,
            'display_name': display_name,
            'photo_url': photo_url,
            'email_verified': user_info.get('email_verified', False),
            'role': role,
            'phone_number': phone_number
        }
        
        # Auto-create threads for campaigns (only for clients and influencers)
        if role in ['client', 'influencer'] and email:
            print(f"📋 Initial thread sync for new user {email}")
            sync_user_campaign_threads(firebase_uid, email, role)
    
    else:
        # User exists, just update last seen and basic info
        user_data = {
            'firebase_uid': firebase_uid,
            'email': email,
            'display_name': existing_user.get('display_name') or user_info.get('name'),
            'photo_url': existing_user.get('photo_url') or user_info.get('picture'),
            'email_verified': user_info.get('email_verified', False),
            'role': existing_user.get('role'),
            'phone_number': existing_user.get('phone_number') or user_info.get('phone_number')
        }
    
    db.create_or_update_user(user_data)
    db.update_user_last_seen(firebase_uid)
    
    return db.get_user_by_firebase_uid(firebase_uid)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Determine file type based on extension"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in {'png', 'jpg', 'jpeg', 'gif'}:
        return 'image'
    elif ext in {'mp4', 'mov', 'avi'}:
        return 'video'
    else:
        return 'file'

def get_image_dimensions(file_path):
    """Extract dimensions from image file"""
    if not PIL_AVAILABLE:
        return None
    try:
        with Image.open(file_path) as img:
            return {"width": img.width, "height": img.height}
    except Exception:
        return None

def get_video_dimensions(file_path):
    """Extract dimensions from video file"""
    if not CV2_AVAILABLE:
        return None
    try:
        video = cv2.VideoCapture(file_path)
        width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        video.release()
        return {"width": width, "height": height}
    except Exception:
        return None

def process_file_upload(file):
    """Process a single file upload and return metadata"""
    if not file or not file.filename or not allowed_file(file.filename):
        return None
    
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{timestamp}_{filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    
    # Save file
    file.save(file_path)
    
    # Get file size
    file_size = os.path.getsize(file_path)
    
    # Determine file type and extract dimensions
    file_type = get_file_type(filename)
    dimensions = None
    
    if file_type == 'image':
        dimensions = get_image_dimensions(file_path)
    elif file_type == 'video':
        dimensions = get_video_dimensions(file_path)
    
    # Create attachment metadata
    attachment = {
        'filename': unique_filename,
        'original_filename': filename,
        'file_path': f'/uploads/{unique_filename}',
        'file_size': file_size,
        'type': file_type
    }
    
    if dimensions:
        attachment['dimensions'] = dimensions
    
    return attachment

# ============================================================================
# THREAD ENDPOINTS (Protected)
# ============================================================================

@app.route('/messages/threads', methods=['GET', 'POST'])
@require_auth
def handle_threads():
    """
    GET: List all threads for authenticated user (auto-syncs with Hyptrb campaigns)
    POST: Create a new thread
    """
    user = get_current_user()
    user_id = user['uid']
    
    # Ensure user exists in database
    db_user = ensure_user_exists(user)
    
    if request.method == 'GET':
        # Always sync threads with Hyptrb campaigns before returning
        user_role = db_user.get('role')
        user_email = db_user.get('email')
        
        print(f"🔍 GET /messages/threads - User: {user_email}, Role: {user_role}")
        
        # If user doesn't have role, try to fetch it from Hyptrb
        if not user_role and user_email:
            print(f"⚠️  User {user_email} has no role, fetching from Hyptrb...")
            try:
                role_data = fetch_user_role(user_email)
                if role_data:
                    user_role = role_data.get('role')
                    print(f"✅ Fetched role: {user_role}")
                    # Update user with role
                    db.create_or_update_user({
                        'firebase_uid': user_id,
                        'email': user_email,
                        'role': user_role,
                        'display_name': db_user.get('display_name'),
                        'photo_url': db_user.get('photo_url'),
                        'phone_number': db_user.get('phone_number'),
                        'email_verified': db_user.get('email_verified', False)
                    })
            except HyptrbAPIError as e:
                print(f"❌ Failed to fetch role: {e}")
        
        if user_role and user_email:
            threads_synced = sync_user_campaign_threads(user_id, user_email, user_role)
            if threads_synced > 0:
                print(f"📊 Synced {threads_synced} new threads for {user_email}")
            else:
                print(f"✓ No new threads to sync for {user_email}")
        else:
            print(f"⏭️  Skipping thread sync - Role: {user_role}, Email: {user_email}")
        
        # Filter threads to only show threads created by the authenticated user
        all_threads = db.get_threads()
        user_threads = [t for t in all_threads if t.get('created_by') == user_id]
        
        print(f"📋 Returning {len(user_threads)} threads for {user_email}")
        
        return jsonify({
            'threads': user_threads,
            'total_count': len(user_threads),
            'user_id': user_id
        })
    
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Add user_id to thread data
        data['created_by'] = user_id
        
        thread_id = db.create_thread(data)
        thread = db.get_thread_by_id(thread_id)
        
        return jsonify({
            'message': 'Thread created successfully',
            'thread': thread
        }), 201

@app.route('/messages/threads/<thread_id>', methods=['GET'])
@require_auth
def get_thread(thread_id):
    """Get thread details with all conversations"""
    user = get_current_user()
    user_id = user['uid']
    ensure_user_exists(user)
    
    if not db.thread_exists(thread_id):
        return jsonify({'error': 'Thread not found'}), 404
    
    thread = db.get_thread_by_id(thread_id)
    
    # Verify user is the thread owner
    if thread.get('created_by') != user_id:
        return jsonify({'error': 'Access denied. You are not the owner of this thread'}), 403
    
    # Only return conversations where the user is a participant
    conversations = db.get_conversations_by_thread(thread_id, user_id=user_id)
    
    return jsonify({
        'thread': thread,
        'conversations': conversations,
        'conversation_count': len(conversations)
    })

# ============================================================================
# CONVERSATION ENDPOINTS (Protected)
# ============================================================================

@app.route('/messages/threads/<thread_id>/conversations', methods=['GET', 'POST'])
@require_auth
def handle_thread_conversations(thread_id):
    """
    GET: List all conversations in a thread
    POST: Create/get conversation between thread owner and another participant
    """
    if not db.thread_exists(thread_id):
        return jsonify({'error': 'Thread not found'}), 404
    
    user = get_current_user()
    user_id = user['uid']
    ensure_user_exists(user)
    
    # Verify user is the thread owner
    thread = db.get_thread_by_id(thread_id)
    if thread.get('created_by') != user_id:
        return jsonify({'error': 'Access denied. You are not the owner of this thread'}), 403
    
    if request.method == 'GET':
        # Only return conversations where the user is a participant
        conversations = db.get_conversations_by_thread(thread_id, user_id=user_id)
        return jsonify({
            'thread_id': thread_id,
            'conversations': conversations,
            'total_count': len(conversations)
        })
    
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            data = {}  # Allow empty body for creating conversation with only owner
        
        # Thread owner is the authenticated user (already verified above)
        thread_owner_id = user_id
        
        # Determine the other participant (optional)
        # Accept either 'other_participant_id' or 'participant2_id' for backwards compatibility
        other_participant_id = data.get('other_participant_id') or data.get('participant2_id')
        
        # Thread owner is always participant1
        participant1_id = thread_owner_id
        participant2_id = other_participant_id  # Can be None
        
        # Fetch participant1 info from database
        participant1_user = db.get_user_by_firebase_uid(participant1_id)
        
        if not participant1_user:
            return jsonify({'error': 'Thread owner not found in database'}), 404
        
        # Use database info for participant1 (thread owner)
        participant1_avatar = participant1_user.get('photo_url', '')
        participant1_name = participant1_user.get('display_name', 'Thread Owner')
        
        # Fetch participant2 info if specified
        participant2_user = None
        participant2_avatar = None
        participant2_name = None
        
        if participant2_id:
            participant2_user = db.get_user_by_firebase_uid(participant2_id)
            if participant2_user:
                participant2_avatar = participant2_user.get('photo_url', '')
                participant2_name = participant2_user.get('display_name', 'Participant')
            else:
                # Fallback to provided values if user doesn't exist yet
                participant2_avatar = data.get('participant2_avatar', '')
                participant2_name = data.get('participant2_name', 'Participant')
        
        # Get conversation name from request or use thread title
        conversation_name = data.get('name')
        if not conversation_name and not participant2_id:
            # For client-only conversations, use thread title + " Discussion"
            thread = db.get_thread_by_id(thread_id)
            if thread:
                conversation_name = f"{thread.get('title', 'Campaign')} Discussion"
        
        # Get or create conversation (with optional participant2)
        conversation_id = db.get_or_create_conversation(
            thread_id=thread_id,
            participant1_id=participant1_id,
            participant2_id=participant2_id,
            participant1_name=participant1_name,
            participant2_name=participant2_name,
            participant1_avatar=participant1_avatar,
            participant2_avatar=participant2_avatar,
            name=conversation_name
        )
        
        conversation = db.get_conversation_by_id(conversation_id)
        
        return jsonify({
            'message': 'Conversation ready',
            'conversation': conversation
        }), 201

@app.route('/messages/threads/<thread_id>/conversations/<conversation_id>/join', methods=['POST'])
@require_auth
def join_conversation(thread_id, conversation_id):
    """
    Join a conversation as participant2
    Only works if conversation has no participant2 yet
    """
    user = get_current_user()
    user_id = user['uid']
    ensure_user_exists(user)
    
    if not db.thread_exists(thread_id):
        return jsonify({'error': 'Thread not found'}), 404
    
    if not db.conversation_exists(conversation_id):
        return jsonify({'error': 'Conversation not found'}), 404
    
    # Get conversation details
    conversation = db.get_conversation_by_id(conversation_id)
    
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    
    # Check if conversation already has participant2
    if conversation.get('participant2_id'):
        return jsonify({
            'error': 'Conversation already has a second participant',
            'participant2_id': conversation.get('participant2_id'),
            'participant2_name': conversation.get('participant2_name')
        }), 400
    
    # Check if user is trying to join their own conversation
    if conversation.get('participant1_id') == user_id:
        return jsonify({'error': 'You cannot join your own conversation as participant2'}), 400
    
    # Get user info from database
    db_user = db.get_user_by_firebase_uid(user_id)
    if not db_user:
        return jsonify({'error': 'User not found in database'}), 404
    
    participant2_name = db_user.get('display_name', 'User')
    participant2_avatar = db_user.get('photo_url', '')
    
    # Update conversation with participant2 info
    success = db.add_participant2_to_conversation(
        conversation_id=conversation_id,
        participant2_id=user_id,
        participant2_name=participant2_name,
        participant2_avatar=participant2_avatar
    )
    
    if not success:
        return jsonify({'error': 'Failed to join conversation'}), 500
    
    # Get updated conversation
    updated_conversation = db.get_conversation_by_id(conversation_id)
    
    return jsonify({
        'message': 'Successfully joined conversation',
        'conversation': updated_conversation
    }), 200

@app.route('/messages/threads/<thread_id>/conversations/<conversation_id>', methods=['GET', 'POST', 'PUT'])
@require_auth
def handle_conversation(thread_id, conversation_id):
    """
    GET: Get all messages in conversation
    POST: Send a new message
    PUT: Mark conversation as read
    """
    if not db.thread_exists(thread_id):
        return jsonify({'error': 'Thread not found'}), 404
    
    if not db.conversation_exists(conversation_id):
        return jsonify({'error': 'Conversation not found'}), 404
    
    # Verify conversation belongs to thread
    conversation = db.get_conversation_by_id(conversation_id)
    if conversation['thread_id'] != thread_id:
        return jsonify({'error': 'Conversation does not belong to this thread'}), 400
    
    user = get_current_user()
    user_id = user['uid']
    ensure_user_exists(user)
    
    # Verify user is a participant in this conversation
    if conversation['participant1_id'] != user_id and conversation['participant2_id'] != user_id:
        return jsonify({'error': 'Access denied. You are not a participant in this conversation'}), 403
    
    # GET: Retrieve messages
    if request.method == 'GET':
        messages = db.get_messages(conversation_id)
        return jsonify({
            'thread_id': thread_id,
            'conversation_id': conversation_id,
            'messages': messages
        })
    
    # PUT: Mark as read
    if request.method == 'PUT':
        result = db.update_conversation_read_status_detailed(conversation_id)
        
        if result['success']:
            response = {
                'message': result['message'],
                'updated': result['updated'],
                'reason': result['reason']
            }
            
            if result['updated'] and 'cleared_unread_count' in result:
                response['cleared_unread_count'] = result['cleared_unread_count']
            
            return jsonify(response)
        else:
            return jsonify({
                'error': result['message'],
                'reason': result['reason']
            }), 404
    
    # POST: Send message
    if request.method == 'POST':
        # Check if this is a multipart/form-data request (with files)
        if request.content_type and 'multipart/form-data' in request.content_type:
            text_content = request.form.get('text', '') or request.form.get('content', '')
            files = request.files.getlist('files')
            
            if not files and not text_content:
                return jsonify({'error': 'No content or files provided'}), 400
            
            # Process uploaded files
            attachments = []
            for file in files:
                attachment = process_file_upload(file)
                if attachment:
                    attachments.append(attachment)
            
            # Get sender info from form or use authenticated user
            sender_id = request.form.get('sender_id', user_id)
            
            # Fetch sender from database to get latest name and avatar
            db_user = db.get_user_by_firebase_uid(sender_id)
            sender_name = (db_user.get('display_name') if db_user 
                          else request.form.get('sender_name', user.get('name', user.get('email', 'User'))))
            
            # Create message data with attachments
            message_data = {
                'conversation_id': conversation_id,
                'thread_id': thread_id,
                'sender_id': sender_id,
                'sender_type': request.form.get('sender_type', 'client'),
                'sender_name': sender_name,
                'type': 'file' if attachments else 'text',
                'content': text_content,
                'text_content': text_content,
                'timestamp': datetime.now().isoformat() + 'Z',
                'status': 'delivered',
                'has_attachment': len(attachments) > 0,
                'attachments': attachments
            }
            
            message_id = db.create_message(message_data)
            message = db.get_message_by_id(message_id)
            
            return jsonify({
                'message': 'Message sent successfully',
                'data': message,
                'attachments_count': len(attachments)
            }), 201
        
        else:
            # Handle JSON request (text-only message)
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Get sender info from request or use authenticated user
            sender_id = data.get('sender_id', user_id)
            
            # Fetch sender from database to get latest name and avatar
            db_user = db.get_user_by_firebase_uid(sender_id)
            sender_name = (db_user.get('display_name') if db_user 
                          else data.get('sender_name', user.get('name', user.get('email', 'User'))))
            
            message_data = {
                'conversation_id': conversation_id,
                'thread_id': thread_id,
                'sender_id': sender_id,
                'sender_type': data.get('sender_type', 'client'),
                'sender_name': sender_name,
                'type': data.get('type', 'text'),
                'content': data.get('content', ''),
                'text_content': data.get('content', ''),
                'timestamp': datetime.now().isoformat() + 'Z',
                'status': 'delivered'
            }
            
            message_id = db.create_message(message_data)
            message = db.get_message_by_id(message_id)
            
            return jsonify({
                'message': 'Message sent successfully',
                'data': message
            }), 201

# ============================================================================
# MESSAGE ENDPOINTS (Protected)
# ============================================================================

@app.route('/messages/threads/<thread_id>/conversations/<conversation_id>/<message_id>', methods=['GET', 'DELETE'])
@require_auth
def handle_message(thread_id, conversation_id, message_id):
    """
    GET: Get specific message details
    DELETE: Delete a message (soft delete)
    """
    # Verify thread exists
    if not db.thread_exists(thread_id):
        return jsonify({'error': 'Thread not found'}), 404
    
    # Verify conversation exists
    if not db.conversation_exists(conversation_id):
        return jsonify({'error': 'Conversation not found'}), 404
    
    # Get message
    message = db.get_message_by_id(message_id)
    
    if not message:
        return jsonify({'error': 'Message not found'}), 404
    
    # Verify message belongs to conversation and thread
    if message['conversation_id'] != conversation_id:
        return jsonify({'error': 'Message does not belong to this conversation'}), 400
    
    if message['thread_id'] != thread_id:
        return jsonify({'error': 'Message does not belong to this thread'}), 400
    
    user = get_current_user()
    ensure_user_exists(user)
    
    # GET: Retrieve message details
    if request.method == 'GET':
        return jsonify({
            'message': message
        })
    
    # DELETE: Soft delete message (only sender can delete)
    if request.method == 'DELETE':
        if message.get('deleted'):
            return jsonify({'message': 'Message already deleted'})
        
        # Verify user is the sender
        if message.get('sender_id') != user['uid']:
            return jsonify({'error': 'You can only delete your own messages'}), 403
        
        success = db.delete_message(message_id)
        
        if success:
            return jsonify({'message': 'Message deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete message'}), 500

# ============================================================================
# FILE UPLOAD ENDPOINTS (Protected)
# ============================================================================

@app.route('/uploads', methods=['POST'])
@require_auth
def upload_files():
    """Upload single or multiple files (requires authentication)"""
    user = get_current_user()
    ensure_user_exists(user)
    
    # Check for multiple files
    files = request.files.getlist('files')
    
    # Fallback to single file if 'files' not present
    if not files or not files[0].filename:
        files = [request.files.get('file')]
    
    if not files or not files[0]:
        return jsonify({'error': 'No files provided'}), 400
    
    uploaded_files = []
    
    for file in files:
        if file and file.filename:
            attachment = process_file_upload(file)
            if attachment:
                uploaded_files.append(attachment)
    
    if not uploaded_files:
        return jsonify({'error': 'No valid files uploaded'}), 400
    
    # Return appropriate response based on number of files
    if len(uploaded_files) == 1:
        return jsonify({
            'message': 'File uploaded successfully',
            **uploaded_files[0]
        }), 201
    else:
        return jsonify({
            'message': f'{len(uploaded_files)} files uploaded successfully',
            'files': uploaded_files
        }), 201

@app.route('/uploads/<filename>', methods=['GET'])
@optional_auth
def serve_file(filename):
    """Serve uploaded file (public access for now, can be restricted)"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ============================================================================
# HEALTH CHECK (Public)
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint (public)"""
    stats = db.get_stats()
    return jsonify({
        'status': 'healthy',
        'service': 'messaging-api',
        'database': 'connected',
        'authentication': 'firebase-admin',
        'stats': stats
    })

@app.route('/auth/test', methods=['GET'])
@require_auth
def test_auth():
    """Test authentication endpoint"""
    user = get_current_user()
    db_user = ensure_user_exists(user)
    
    return jsonify({
        'message': 'Authentication successful',
        'user': {
            'uid': user['uid'],
            'email': user.get('email'),
            'name': user.get('name'),
            'email_verified': user.get('email_verified', False)
        },
        'database_user': db_user
    })

# ============================================================================
# USER MANAGEMENT ENDPOINTS (Protected)
# ============================================================================

@app.route('/users/me', methods=['GET', 'PUT'])
@require_auth
def handle_current_user():
    """
    GET: Get current user profile
    PUT: Update current user profile
    """
    user = get_current_user()
    user_id = user['uid']
    
    if request.method == 'GET':
        db_user = ensure_user_exists(user)
        return jsonify({
            'user': db_user
        })
    
    if request.method == 'PUT':
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update user data
        user_data = {
            'firebase_uid': user_id,
            'email': user.get('email'),
            'display_name': data.get('display_name') or user.get('name'),
            'photo_url': data.get('photo_url') or user.get('picture'),
            'role': data.get('role'),
            'phone_number': data.get('phone_number'),
            'email_verified': user.get('email_verified', False)
        }
        
        db.create_or_update_user(user_data)
        updated_user = db.get_user_by_firebase_uid(user_id)
        
        return jsonify({
            'message': 'User profile updated successfully',
            'user': updated_user
        })

@app.route('/users/<firebase_uid>', methods=['GET'])
@require_auth
def get_user(firebase_uid):
    """Get user by Firebase UID"""
    user = db.get_user_by_firebase_uid(firebase_uid)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user': user
    })

@app.route('/users', methods=['GET'])
@require_auth
def list_users():
    """List all users with pagination"""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    users = db.get_all_users(limit=limit, offset=offset)
    
    return jsonify({
        'users': users,
        'total_count': len(users),
        'limit': limit,
        'offset': offset
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
