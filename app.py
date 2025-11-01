from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import time
from werkzeug.utils import secure_filename
from db import get_db
import json
from firebase_auth import initialize_firebase, require_auth, optional_auth, get_current_user
from hyptrb_api import (
    fetch_influencer_jobs,
    fetch_user_role, 
    fetch_user_profile_by_role, 
    extract_display_name,
    fetch_client_campaigns,
    fetch_influencer_collaborations,
    HyptrbAPIError
)
from admin_blueprint import admin_blueprint

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
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

# Track start time for uptime
START_TIME = time.time()

# Initialize Firebase Admin SDK
FIREBASE_INITIALIZED = False
try:
    initialize_firebase()
    FIREBASE_INITIALIZED = True
except Exception as e:
    print(f"⚠️  Warning: Firebase initialization failed: {e}")
    print("   API will continue but authentication will not work")

# File upload configuration
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
ALLOWED_EXTENSIONS = None  # Allow all file types
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 104857600))  # Default: 100MB (100 * 1024 * 1024)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize database
db = get_db()

# Register admin blueprint
app.register_blueprint(admin_blueprint)

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
            # Fetch influencer jobs/campaigns (fetch all pages)
            all_jobs = []
            page = 1
            
            # Fetch first page to get total info
            jobs_data = fetch_influencer_jobs(firebase_uid, page=1)
            total_jobs = jobs_data.get('totalJobs', 0)
            total_pages = jobs_data.get('totalPages', 1)
            all_jobs.extend(jobs_data.get('jobs', []))
            
            print(f"🔄 Syncing {total_jobs} jobs across {total_pages} pages for influencer {firebase_uid}")
            
            # Fetch remaining pages if any
            for page in range(2, total_pages + 1):
                try:
                    jobs_data = fetch_influencer_jobs(firebase_uid, page=page)
                    all_jobs.extend(jobs_data.get('jobs', []))
                except Exception as e:
                    print(f"  ⚠️  Failed to fetch page {page}: {e}")
            
            # Group jobs by campaign to avoid duplicate threads
            campaigns_dict = {}
            for job in all_jobs:
                # Extract campaign details from the job
                campaign_details_list = job.get('campaignDetails', [])
                if campaign_details_list and len(campaign_details_list) > 0:
                    campaign_detail = campaign_details_list[0]
                    campaign_id = campaign_detail.get('campaignId')
                    campaign_name = campaign_detail.get('campaignName', 'Unnamed Campaign')
                    
                    if campaign_id and campaign_id not in campaigns_dict:
                        campaigns_dict[campaign_id] = campaign_name
            
            print(f"  📊 Found {len(campaigns_dict)} unique campaigns from {len(all_jobs)} jobs")
            
            # Create thread for each unique campaign
            for campaign_id, campaign_name in campaigns_dict.items():
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
                    # Thread might already exist (UNIQUE constraint on campaign_id + created_by)
                    if 'UNIQUE constraint failed' not in str(e):
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
    # Validate user_info is a dictionary
    if not isinstance(user_info, dict):
        raise ValueError(f"user_info must be a dictionary, got {type(user_info).__name__}: {user_info}")
    
    firebase_uid = user_info.get('uid')
    if not firebase_uid:
        raise ValueError("user_info must contain 'uid' field")
    
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
    """Check if file extension is allowed (all files allowed if ALLOWED_EXTENSIONS is None)"""
    if ALLOWED_EXTENSIONS is None:
        return True  # Allow all file types
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Determine file type based on extension"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    # Image types
    if ext in {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg', 'ico', 'tiff', 'tif'}:
        return 'image'
    
    # Video types
    elif ext in {'mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'wmv', 'm4v', 'mpeg', 'mpg'}:
        return 'video'
    
    # Default to file for everything else
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

def determine_message_type(message: dict) -> str:
    """
    Determine message type at runtime based on content and attachments.
    Returns: 'text', 'image', 'video', 'file', 'image+text', 'video+text', 'file+text'
    """
    has_text = bool(message.get('text_content') or message.get('content', '').strip())
    has_attachment = message.get('has_attachment', False)
    
    if not has_attachment:
        return 'text'
    
    # Get attachments
    attachments = message.get('attachments', [])
    
    # Handle case where attachments might be a JSON string (shouldn't happen after db.py fix)
    if isinstance(attachments, str):
        try:
            import json
            attachments = json.loads(attachments)
        except (json.JSONDecodeError, TypeError):
            attachments = []
    
    if not attachments or not isinstance(attachments, list):
        # Legacy format - check for filename field
        if message.get('filename'):
            file_type = get_file_type(message.get('filename', ''))
            return f"{file_type}+text" if has_text else file_type
        return 'text'
    
    # Determine primary attachment type (use first attachment's type)
    first_attachment = attachments[0]
    if isinstance(first_attachment, dict):
        primary_type = first_attachment.get('type', 'file')
    else:
        # Fallback if attachment is not a dict
        primary_type = 'file'
    
    # Return combined type if text is present
    if has_text:
        return f"{primary_type}+text"
    else:
        return primary_type

# ============================================================================
# THREAD ENDPOINTS (Protected)
# ============================================================================

@app.route('/messages/threads', methods=['GET', 'POST'])
@require_auth
def handle_threads():
    """
    GET: List all threads for authenticated user (auto-syncs with Hyptrb campaigns)
         Each thread includes:
         - conversation_count: Number of conversations in the thread
         - conversations: Simplified list of conversations with essential fields
           - last_message_type: Computed at runtime (text, image, video, file, image+text, video+text, file+text)
    POST: Create a new thread (includes conversation data in response)
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
        
        # Get threads where user is creator OR participant in any conversation
        user_threads = db.get_threads_for_user(user_id)
        
        # Enrich each thread with conversation data
        for thread in user_threads:
            thread_id = thread['id']
            conversations = db.get_conversations_by_thread(thread_id, user_id=user_id)
            
            # Add conversation count
            thread['conversation_count'] = len(conversations)
            
            # Add simplified conversation list (only essential fields)
            enriched_conversations = []
            for conv in conversations:
                # Get last message to determine type
                last_msg = db.get_last_message(conv['id'])
                last_message_type = determine_message_type(last_msg) if last_msg else 'text'
                
                enriched_conversations.append({
                    'id': conv['id'],
                    'name': conv.get('name'),
                    'participant1_id': conv.get('participant1_id'),
                    'participant1_name': conv.get('participant1_name'),
                    'participant2_id': conv.get('participant2_id'),
                    'participant2_name': conv.get('participant2_name'),
                    'last_message': conv.get('last_message'),
                    'last_message_time': conv.get('last_message_time'),
                    'last_message_type': last_message_type,
                    'unread_count': conv.get('unread_count', 0),
                    'updated_at': conv.get('updated_at')
                })
            
            thread['conversations'] = enriched_conversations
        
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
        
        # Enrich thread with conversation data
        conversations = db.get_conversations_by_thread(thread_id, user_id=user_id)
        thread['conversation_count'] = len(conversations)
        
        enriched_conversations = []
        for conv in conversations:
            # Get last message to determine type
            last_msg = db.get_last_message(conv['id'])
            last_message_type = determine_message_type(last_msg) if last_msg else 'text'
            
            enriched_conversations.append({
                'id': conv['id'],
                'name': conv.get('name'),
                'participant1_id': conv.get('participant1_id'),
                'participant1_name': conv.get('participant1_name'),
                'participant2_id': conv.get('participant2_id'),
                'participant2_name': conv.get('participant2_name'),
                'last_message': conv.get('last_message'),
                'last_message_time': conv.get('last_message_time'),
                'last_message_type': last_message_type,
                'unread_count': conv.get('unread_count', 0),
                'updated_at': conv.get('updated_at')
            })
        
        thread['conversations'] = enriched_conversations
        
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
    
    # Verify user has access to thread (creator or participant)
    if not db.user_has_thread_access(thread_id, user_id):
        return jsonify({'error': 'Access denied. You do not have access to this thread'}), 403
    
    thread = db.get_thread_by_id(thread_id)
    
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
    
    thread = db.get_thread_by_id(thread_id)
    
    if request.method == 'GET':
        # Verify user has access to thread (creator or participant)
        if not db.user_has_thread_access(thread_id, user_id):
            return jsonify({'error': 'Access denied. You do not have access to this thread'}), 403
        
        # Only return conversations where the user is a participant
        conversations = db.get_conversations_by_thread(thread_id, user_id=user_id)
        return jsonify({
            'thread_id': thread_id,
            'conversations': conversations,
            'total_count': len(conversations)
        })
    
    if request.method == 'POST':
        # For POST, verify user is the thread owner (only owner can create conversations)
        if thread.get('created_by') != user_id:
            return jsonify({'error': 'Access denied. Only the thread owner can create conversations'}), 403
        
        data = request.get_json()
        if not data:
            data = {}  # Allow empty body for creating conversation with only owner
        
        # Thread owner is the authenticated user
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

@app.route('/messages/campaigns/<campaign_id>/join', methods=['POST'])
@require_auth
def join_campaign(campaign_id):
    """
    Join a campaign thread as an admin
    Only admins can join campaigns
    Creates a conversation between the admin and the campaign owner
    """
    user = get_current_user()
    user_id = user['uid']
    db_user = ensure_user_exists(user)
    
    # Check if user is an admin
    user_role = db_user.get('role')
    if user_role != 'admin':
        return jsonify({
            'error': 'Access denied. Only admins can join campaigns',
            'user_role': user_role
        }), 403
    
    # Find thread by campaign_id
    conn = db.get_connection()
    try:
        cursor = conn.execute('SELECT * FROM threads WHERE campaign_id = ?', (campaign_id,))
        thread_row = cursor.fetchone()
        
        if not thread_row:
            return jsonify({'error': 'Campaign thread not found'}), 404
        
        thread = dict(thread_row)
        thread_id = thread['id']
        campaign_owner_id = thread['created_by']
        
        # Check if admin is trying to join their own campaign
        if campaign_owner_id == user_id:
            return jsonify({'error': 'You cannot join your own campaign'}), 400
        
        # Get campaign owner info
        owner_user = db.get_user_by_firebase_uid(campaign_owner_id)
        if not owner_user:
            return jsonify({'error': 'Campaign owner not found in database'}), 404
        
        # Get admin info
        admin_name = db_user.get('display_name', 'Admin')
        admin_avatar = db_user.get('photo_url', '')
        
        # Create or get conversation between campaign owner and admin
        conversation_name = f"{thread.get('title', 'Campaign')} - Admin Support"
        
        conversation_id = db.get_or_create_conversation(
            thread_id=thread_id,
            participant1_id=campaign_owner_id,
            participant2_id=user_id,
            participant1_name=owner_user.get('display_name', 'Campaign Owner'),
            participant2_name=admin_name,
            participant1_avatar=owner_user.get('photo_url', ''),
            participant2_avatar=admin_avatar,
            name=conversation_name
        )
        
        conversation = db.get_conversation_by_id(conversation_id)
        
        return jsonify({
            'message': 'Successfully joined campaign',
            'campaign_id': campaign_id,
            'thread_id': thread_id,
            'conversation': conversation
        }), 200
        
    finally:
        conn.close()

@app.route('/messages/admin/chat/<user_firebase_uid>', methods=['POST'])
@require_auth
def admin_start_chat(user_firebase_uid):
    """
    Start a direct chat with any user as an admin
    Only admins can use this endpoint
    Creates a dedicated admin support thread and conversation
    """
    user = get_current_user()
    admin_id = user['uid']
    db_user = ensure_user_exists(user)
    
    # Check if user is an admin
    admin_role = db_user.get('role')
    if admin_role != 'admin':
        return jsonify({
            'error': 'Access denied. Only admins can start direct chats',
            'user_role': admin_role
        }), 403
    
    # Check if admin is trying to chat with themselves
    if user_firebase_uid == admin_id:
        return jsonify({'error': 'You cannot start a chat with yourself'}), 400
    
    # Get target user info
    target_user = db.get_user_by_firebase_uid(user_firebase_uid)
    if not target_user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get admin info
    admin_name = db_user.get('display_name', 'Admin')
    admin_avatar = db_user.get('photo_url', '')
    
    target_name = target_user.get('display_name', 'User')
    target_avatar = target_user.get('photo_url', '')
    
    # Create or get admin support thread for this user
    # Use a special campaign_id format for admin chats: "admin_support_{user_uid}"
    admin_thread_campaign_id = f"admin_support_{user_firebase_uid}"
    
    thread_data = {
        'title': f"Admin Support - {target_name}",
        'description': f"Direct admin support chat with {target_name}",
        'campaign_id': admin_thread_campaign_id,
        'created_by': admin_id,
        'status': 'active'
    }
    
    try:
        thread_id = db.create_thread(thread_data)
        thread = db.get_thread_by_id(thread_id)
        
        # Create or get conversation between admin and user
        conversation_name = f"Admin Support - {target_name}"
        
        conversation_id = db.get_or_create_conversation(
            thread_id=thread_id,
            participant1_id=admin_id,
            participant2_id=user_firebase_uid,
            participant1_name=admin_name,
            participant2_name=target_name,
            participant1_avatar=admin_avatar,
            participant2_avatar=target_avatar,
            name=conversation_name
        )
        
        conversation = db.get_conversation_by_id(conversation_id)
        
        return jsonify({
            'message': 'Admin chat started successfully',
            'user_firebase_uid': user_firebase_uid,
            'thread_id': thread_id,
            'thread': thread,
            'conversation': conversation
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to create admin chat',
            'details': str(e)
        }), 500

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
# FILE SERVING ENDPOINT (Public)
# ============================================================================

@app.route('/uploads/<filename>', methods=['GET'])
@optional_auth
def serve_file(filename):
    """Serve uploaded files (files are uploaded as part of message sending)"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ============================================================================
# HEALTH CHECK & STATUS PAGE (Public)
# ============================================================================

@app.route('/', methods=['GET'])
def index():
    """Redirect to admin login"""
    return redirect(url_for('admin_blueprint.login'))

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker (public)"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
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

# ============================================================================
# INFLUENCER JOBS ENDPOINTS (Protected)
# ============================================================================

@app.route('/influencer/jobs/<influencer_uid>', methods=['GET'])
@require_auth
def get_influencer_jobs(influencer_uid):
    """
    Get jobs/campaigns for an influencer
    
    Query Parameters:
    - page: Page number for pagination (default: 1)
    
    Returns:
    - influencer_uid: Influencer's UID
    - totalJobs: Total number of jobs
    - totalPages: Total number of pages
    - currentPage: Current page number
    - jobs: List of job objects with campaign details, status, rates, postLinks, etc.
    """
    user = get_current_user()
    
    # Verify user is authorized to view this influencer's jobs
    # Either the user is the influencer themselves or an admin
    db_user = ensure_user_exists(user)
    user_role = db_user.get('role', 'client')
    
    if user_role != 'admin' and user['uid'] != influencer_uid:
        return jsonify({'error': 'Unauthorized to view these jobs'}), 403
    
    # Get page parameter
    page = request.args.get('page', 1, type=int)
    
    try:
        # Fetch jobs from Hyptrb API
        jobs_data = fetch_influencer_jobs(influencer_uid, page=page)
        
        return jsonify(jobs_data), 200
        
    except HyptrbAPIError as e:
        return jsonify({
            'error': 'Failed to fetch influencer jobs',
            'details': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

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
    # Load configuration from environment variables
    debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')
    api_host = os.getenv('API_HOST', '0.0.0.0')
    api_port = int(os.getenv('API_PORT', 5001))
    
    app.run(debug=debug_mode, host=api_host, port=api_port)
