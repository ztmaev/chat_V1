# InfluencerConnect Chat API

**Secure, thread-based messaging API with Firebase authentication**

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# 1. Add your Firebase service account key
# Download from Firebase Console → Project Settings → Service Accounts
# Save as: serviceAccountKey.json

# 2. Start with Docker
./docker-start.sh start

# View logs
./docker-start.sh logs
```

### Option 2: Local Python

```bash
# 1. Run setup script
./setup_firebase.sh

# 2. Add your Firebase service account key
# Download from Firebase Console → Project Settings → Service Accounts
# Save as: serviceAccountKey.json

# 3. Start the API
source .venv/bin/activate
python3 app.py
```

The API will be available at `http://localhost:5001`

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Setup](#quick-setup)
- [Docker Setup](#docker-setup)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
- [Database Structure](#database-structure)
- [Development](#development)

## 🎯 Overview

This is a production-ready messaging API for the InfluencerConnect platform. It provides:

- **Thread-based conversations** - Organize messages by campaign/topic
- **Firebase authentication** - Secure access with Firebase ID tokens
- **File attachments** - Images, videos, documents with metadata
- **SQLite database** - Persistent storage with triggers and indexes
- **RESTful API** - Clean, documented endpoints

## ✨ Features

### Security
- ✅ Firebase Admin SDK authentication
- ✅ Token-based access control
- ✅ User context in all requests
- ✅ Authorization checks (users can only delete own messages)
- ✅ **Hyptrb API integration** - Auto-fetch user roles and profiles
- ✅ **Thread ownership** - Only thread owners can access and manage threads

### Messaging
- ✅ **Automatic thread creation** - Threads auto-created from Hyptrb campaigns
- ✅ Thread-based organization with user ownership
- ✅ One thread per campaign per user (clients and influencers get separate threads)
- ✅ Conversations automatically include thread owner
- ✅ Multi-participant conversations (thread owner + one other user)
- ✅ Text and file messages
- ✅ Multiple attachments per message
- ✅ Soft delete (preserves history)
- ✅ Read/unread status tracking

### File Handling
- ✅ Multiple file uploads
- ✅ Image dimension extraction (PIL)
- ✅ Video dimension extraction (OpenCV)
- ✅ File size tracking
- ✅ Type detection (image/video/file)
- ✅ Secure file serving

### Database
- ✅ SQLite with proper schema
- ✅ Foreign key constraints
- ✅ Database triggers for auto-updates
- ✅ Performance indexes
- ✅ Migration scripts

## 🔧 Quick Setup

### Prerequisites

- Python 3.7+
- pip
- Firebase project with Authentication enabled

### Installation

```bash
# Clone and navigate to directory
cd inDev/chatAPI

# Run automated setup
./setup_firebase.sh

# Or manual setup:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Firebase Configuration

1. **Get Service Account Key:**
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Select your project
   - **Project Settings** → **Service Accounts**
   - Click **Generate New Private Key**
   - Save as `serviceAccountKey.json` in this directory

2. **Verify Setup:**
   ```bash
   # Should see: ✅ Firebase Admin initialized
   python3 app.py
   ```

### Initialize Database

```bash
# Populate with demo data
python3 setup_demo_data.py
```

## 🐳 Docker Setup

The Chat API can be easily deployed using Docker and Docker Compose.

### Quick Docker Start

```bash
# Start the API with Docker
./docker-start.sh start

# View logs
./docker-start.sh logs

# Stop the API
./docker-start.sh stop
```

### Docker Commands

```bash
# Start in production mode
./docker-start.sh start prod

# Rebuild after code changes
./docker-start.sh rebuild

# Backup database
./docker-start.sh backup

# Initialize with demo data
./docker-start.sh init

# View status
./docker-start.sh status

# Access container shell
./docker-start.sh shell
```

### Manual Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f chat-api

# Stop services
docker-compose down

# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Docker Features

- ✅ Automated container setup with health checks
- ✅ Persistent database and uploads via volumes
- ✅ Production-ready configuration
- ✅ Resource limits and logging
- ✅ Easy backup and restore
- ✅ Isolated network for security

### Using Make Commands

```bash
make start      # Start API
make prod       # Start in production mode
make stop       # Stop API
make logs       # View logs
make test       # Run Docker tests
make backup     # Backup database
make help       # Show all commands
```

### Troubleshooting Docker

```bash
# Container won't start
./docker-start.sh logs

# Port 5001 in use
sudo lsof -i :5001

# Rebuild container
./docker-start.sh rebuild

# Run diagnostic tests
./test-docker-setup.sh
```

## 🔐 Authentication

All messaging endpoints require Firebase authentication.

### Client-Side (Frontend)

```typescript
import { auth } from '@/config/firebase';

// Get Firebase ID token
const user = auth.currentUser;
const idToken = await user.getIdToken();

// Include in API requests
fetch('http://localhost:5001/messages/threads', {
  headers: {
    'Authorization': `Bearer ${idToken}`,
  },
});
```

### Testing Authentication

```bash
# Get token from frontend, then:
curl -H "Authorization: Bearer <token>" \
     http://localhost:5001/auth/test
```

### Automatic User Profile Enrichment

When a user accesses the API for the first time (or if their role is missing), the system automatically:

1. **Fetches user role** from Hyptrb API: `GET https://api.hyptrb.africa/roles/{email}`
2. **Fetches profile data** based on role:
   - **Client**: `GET https://api.hyptrb.africa/clients/get/{email}` → Uses `businessName`
   - **Admin**: `GET https://api.hyptrb.africa/admin/profile/{email}` → Uses `name`
   - **Influencer**: `GET https://api.hyptrb.africa/influencer/get/profile/{uid}` → Uses `full_name`, `profile_picture_url`
3. **Updates database** with enriched profile information (display_name, role, photo_url, phone_number)
4. **Fetches campaigns** and auto-creates threads (for clients and influencers only):
   - **Client**: `GET https://api.hyptrb.africa/clients/get/all/campaigns/{email}` → Creates thread per campaign
   - **Influencer**: `GET https://api.hyptrb.africa/influencer/get/clients/collaborations/{uid}` → Creates thread per current campaign
5. **Conversations and messages** automatically use the stored avatar from database

This ensures users have proper display names, role information, and campaign-based threads without manual setup.

**Example Flow:**
```
User Login → Firebase Auth → API Request
                              ↓
                    Check local database
                              ↓
                    No role found? → Fetch from Hyptrb
                              ↓
                    GET /roles/{email}
                              ↓
                    role = "client"
                              ↓
                    GET /clients/get/{email}
                              ↓
                    Extract businessName & photo
                              ↓
                    GET /clients/get/all/campaigns/{email}
                              ↓
                    Create threads for each campaign
                    (one thread per campaign_id)
                              ↓
                    Update local database
                              ↓
                    Continue with request
```

**Graceful Fallback:**
- If Hyptrb API is unavailable, user is created with basic Firebase info
- Role can be updated later when API becomes available
- System logs warnings but doesn't block user access

**Testing:**
```bash
# Test Hyptrb integration
source .venv/bin/activate
python3 test_hyptrb_integration.py
```


## 📡 API Endpoints

### Authentication Test
- `GET /auth/test` - Verify authentication (requires token)
- `GET /health` - Health check (public)

### User Management
- `GET /users/me` - Get current user profile
- `GET /users` - List all users (paginated, limit/offset params)
- `GET /users/<firebase_uid>` - Get specific user by Firebase UID

**Note:** Users are automatically created/updated on any authenticated request.

### Threads
- `GET /messages/threads` - List all threads (owned by authenticated user)
- `GET /messages/threads/<thread_id>` - Get thread details (owner only)

**Automatic Thread Creation & Sync:**
- Threads are **automatically created** when users first access the API
- Threads are **automatically synced** every time `GET /messages/threads` is called
- Each campaign from Hyptrb gets its own thread
- **Clients**: One thread per campaign they created
- **Influencers**: One thread per campaign they're collaborating on
- **Admins**: No automatic threads (development UI only)
- Thread creation is idempotent (won't create duplicates)
- **Always up-to-date**: New campaigns in Hyptrb automatically appear as threads

**Thread Schema:**
- Each thread is linked to a Hyptrb `campaign_id`
- UNIQUE constraint: One thread per `(campaign_id, created_by)` combination
- Clients and influencers get separate threads for the same campaign
- Thread title: "Campaign: {campaign_name}"

### Conversations
- `GET /messages/threads/<thread_id>/conversations` - List conversations (owner only)
- `POST /messages/threads/<thread_id>/conversations` - Create conversation
- `POST /messages/threads/<thread_id>/conversations/<conversation_id>/join` - Join conversation as participant2
- `GET /messages/threads/<thread_id>/conversations/<conversation_id>` - Get messages
- `POST /messages/threads/<thread_id>/conversations/<conversation_id>` - Send message
- `PUT /messages/threads/<thread_id>/conversations/<conversation_id>` - Mark as read

**Conversation Creation:**
- Thread owner creates conversation (becomes `participant1`)
- `other_participant_id` is **optional** - can start conversation alone
- Thread owner can send messages immediately, even without participant2
- Names and avatars fetched from database automatically

**Joining Conversations:**
- Other users can join a conversation with `POST .../join`
- Only works if conversation has no `participant2` yet
- Joining user becomes `participant2`
- Cannot join your own conversation

### Messages
- `GET /messages/threads/<thread_id>/conversations/<conversation_id>/<message_id>` - Get message
- `DELETE /messages/threads/<thread_id>/conversations/<conversation_id>/<message_id>` - Delete message

### Files
- `POST /uploads` - Upload files
- `GET /uploads/<filename>` - Serve uploaded file

### Example: List Threads

```bash
# Threads are automatically created from campaigns
# Just list them with authentication
curl -X GET \
  -H "Authorization: Bearer <firebase-token>" \
  http://localhost:5001/messages/threads
```

### Example: Create Conversation (Owner Only)

```bash
# Thread owner creates conversation alone
curl -X POST \
  -H "Authorization: Bearer <firebase-token>" \
  http://localhost:5001/messages/threads/thread_1/conversations

# Or with a second participant immediately
curl -X POST \
  -H "Authorization: Bearer <firebase-token>" \
  -H "Content-Type: application/json" \
  -d '{"other_participant_id": "influencer_firebase_uid"}' \
  http://localhost:5001/messages/threads/thread_1/conversations
```

### Example: Join Conversation

```bash
# Another user joins an existing conversation
curl -X POST \
  -H "Authorization: Bearer <firebase-token>" \
  http://localhost:5001/messages/threads/thread_1/conversations/conv_123/join
```

### Example: Send Message

```bash
curl -X POST \
  -H "Authorization: Bearer <firebase-token>" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello!"}' \
  http://localhost:5001/messages/threads/thread_1/conversations/conv_1
```

### Example: Upload File with Message

```bash
curl -X POST \
  -H "Authorization: Bearer <firebase-token>" \
  -F "text=Check out this image" \
  -F "files=@image.jpg" \
  http://localhost:5001/messages/threads/thread_1/conversations/conv_1
```

## 🗄️ Database Structure

### Tables

**users**
- Stores Firebase user information
- Primary key: `firebase_uid`
- Fields: email, display_name, photo_url, role, phone_number, email_verified, last_seen
- Automatically populated from Firebase Auth on any API request

**threads**
- Campaign-based message organization (auto-created from Hyptrb)
- Fields: id, title, description, `campaign_id`, `created_by`, status, timestamps
- **Campaign Link:** Each thread is linked to a Hyptrb campaign via `campaign_id`
- **Ownership:** Each thread has one owner (the client or influencer)
- **Uniqueness:** UNIQUE(campaign_id, created_by) - one thread per campaign per user
- **Access Control:** Only thread owners can view and manage their threads
- **Automatic:** Created on first API access for clients and influencers

**conversations**
- Chats within threads (1 or 2 participants)
- `participant1_id` (required) - Usually the thread owner who created the conversation
- `participant2_id` (optional) - Can be NULL, added later via join endpoint
- Tracks last message, unread count, participant names and avatars
- **Solo start:** Conversations can be created with only participant1
- **Join later:** participant2 can join via `/join` endpoint
- **Access Control:** Users can only see conversations they're participants in

**messages**
- Individual messages
- Supports text, files, or both
- Soft delete capability
- Attachment metadata with dimensions

### Triggers

- Auto-update conversation last_message
- Auto-update conversation timestamps
- Handle deleted message updates

### Indexes

- Performance optimization on frequently queried fields
- Foreign key relationships



## 🛠️ Development

### Project Structure

```
chatAPI/
├── app.py                          # Main API (secured with Firebase)
├── firebase_auth.py                # Authentication module
├── db.py                           # Database operations
├── demodata.py                     # Sample data
├── setup_demo_data.py           # Database migration
├── requirements.txt                # Python dependencies
├── serviceAccountKey.json          # Firebase credentials (gitignored)
├── messaging.db                    # SQLite database (gitignored)
├── uploads/                        # File uploads (gitignored)
└── .venv/                          # Virtual environment (gitignored)
```

### Running the API

```bash
# Activate virtual environment
source .venv/bin/activate

# Development mode (with debug)
python3 app.py

# Production mode
FLASK_ENV=production python3 app.py
```

### Environment Variables

Create `.env` file (see `.env.example`):

```bash
# Firebase
FIREBASE_SERVICE_ACCOUNT_KEY=serviceAccountKey.json

# API Configuration
FLASK_ENV=development
FLASK_DEBUG=True
API_PORT=5001
API_HOST=0.0.0.0
```

### Testing

```bash
# Test authentication
curl -H "Authorization: Bearer <token>" \
     http://localhost:5001/auth/test

# Test health endpoint (no auth required)
curl http://localhost:5001/health

# Test thread listing
curl -H "Authorization: Bearer <token>" \
     http://localhost:5001/messages/threads
```

## 🔒 Security Best Practices

### Access Control (Updated 2025-10-11)

**✅ FIXED: Conversation Access Control Vulnerability**

Previously, users could view all conversations in a thread regardless of participation. This has been fixed:

- **Database Layer:** `get_conversations_by_thread()` now filters by `user_id`
- **SQL Filtering:** `WHERE (participant1_id = ? OR participant2_id = ?)`
- **API Layer:** All conversation endpoints now pass authenticated user's ID
- **Message Access:** Added verification that user is a participant before allowing message operations
- **HTTP Status:** Returns `403 Forbidden` for unauthorized access attempts

**Security Rules:**
1. ✅ Users can ONLY see conversations where they are participant1 or participant2
2. ✅ Users can ONLY read messages from their own conversations
3. ✅ Users can ONLY send messages to their own conversations
4. ✅ Database-level filtering (efficient and secure)
5. ✅ No sensitive data ever loaded into memory for unauthorized users

**Testing Access Control:**
```bash
# User A creates conversation with User C
# User B tries to fetch conversations - should NOT see User A's conversation
curl -H "Authorization: Bearer <user-b-token>" \
     http://localhost:5001/messages/threads/thread_1/conversations

# User B tries to access User A's conversation directly - should get 403
curl -H "Authorization: Bearer <user-b-token>" \
     http://localhost:5001/messages/threads/thread_1/conversations/conv_1/messages
```

### Development
- ✅ Never commit `serviceAccountKey.json`
- ✅ Use `.env` for configuration
- ✅ Test with real Firebase tokens
- ✅ Verify token expiration handling
- ✅ Test access control with multiple user accounts

### Production
- ✅ Use environment variables for credentials
- ✅ Enable HTTPS only
- ✅ Restrict CORS origins
- ✅ Implement rate limiting
- ✅ Monitor authentication logs
- ✅ Rotate service account keys periodically
- ✅ Set proper file permissions (600 for keys)
- ✅ Audit access control logs for 403 errors

## 🚨 Troubleshooting

### Firebase Not Initializing

**Problem:** `⚠️ WARNING: No Firebase credentials found`

**Solution:**
```bash
# Verify file exists
ls -la serviceAccountKey.json

# Check permissions
chmod 600 serviceAccountKey.json

# Set environment variable
export FIREBASE_SERVICE_ACCOUNT_KEY="serviceAccountKey.json"
```

### Authentication Failing

**Problem:** All requests return 401

**Solutions:**
1. Verify Firebase project ID matches frontend/backend
2. Check user is signed in on frontend
3. Verify token is in Authorization header
4. Check token hasn't expired (refresh after 1 hour)

### Database Issues

**Problem:** Database errors or missing tables

**Solution:**
```bash
# Reinitialize database
rm messaging.db
python3 setup_demo_data.py
```

## 📦 Dependencies

```
Flask==2.3.3              # Web framework
Flask-CORS==4.0.0         # CORS support
firebase-admin==6.2.0     # Firebase authentication
Pillow==10.0.1            # Image processing
opencv-python==4.8.1.78   # Video processing
numpy<2                   # OpenCV compatibility
```

## 🔄 Migration from Unsecured API

If you have an existing unsecured version:

1. **Backup current version:**
   ```bash
   cp app.py app_insecure.py.bak
   ```

2. **Current version is already secured** - `app.py` now uses Firebase auth


4. **Test thoroughly** before removing backup

## 📝 API Response Format

### Success Response

```json
{
  "message": "Message sent successfully",
  "data": {
    "id": "msg_123",
    "content": "Hello!",
    "sender_id": "firebase-uid",
    "timestamp": "2024-01-10T08:00:00Z"
  }
}
```

### Error Response

```json
{
  "error": "Authentication required",
  "message": "No Firebase ID token provided. Include token in Authorization header as \"Bearer <token>\""
}
```

## 🤝 Contributing

1. Follow existing code style
2. Add tests for new features
3. Update documentation
4. Ensure Firebase auth is maintained

## 📄 License

Part of the InfluencerConnect project.

## 🆘 Support

For issues or questions:
1. Check documentation in this directory
2. Review Firebase Console for auth errors
3. Check server logs for detailed errors
4. Test with `/auth/test` endpoint

## 🎯 Next Steps

After setup:

1. ✅ **Frontend Integration** - Update API calls to include Firebase tokens
2. ✅ **User Association** - Link threads/conversations to Firebase users
3. ✅ **Role-Based Access** - Implement client/influencer permissions
4. ✅ **Production Deployment** - Deploy with proper security
5. ✅ **Monitoring** - Add logging and analytics

## 📝 Version History

### Version 2.5.0 - Optional Participant2 & Join Endpoint (2025-10-12)
**Flexible Conversation Model**
- ✅ `participant2` is now optional in conversations
- ✅ Thread owners can create conversations and start messaging alone
- ✅ New endpoint: `POST .../conversations/<id>/join` for joining conversations
- ✅ `add_participant2_to_conversation()` database method
- ✅ Updated conversation schema - participant2 fields nullable
- ✅ Migration script `migrate_optional_participant2.py`
- ✅ Validation: Users cannot join their own conversation
- ✅ Validation: Cannot join conversation that already has participant2

**Workflow Changes:**
- Create conversation without specifying participant2
- Send messages in solo conversation
- Other users discover and join conversations
- participant2 automatically populated with user info on join

### Version 2.4.0 - Automatic Campaign-Based Threads (2025-10-12)
**Automatic Thread Creation from Hyptrb Campaigns**
- ✅ Threads automatically created from Hyptrb campaigns on first user access
- ✅ **Always-on sync**: `GET /messages/threads` syncs with Hyptrb on every call
- ✅ Old users get threads automatically synced when they call the endpoint
- ✅ New campaigns in Hyptrb automatically appear as threads
- ✅ Added `campaign_id` field to threads table
- ✅ UNIQUE constraint on (campaign_id, created_by) - prevents duplicate threads
- ✅ Client threads: Auto-created from all campaigns owned by client
- ✅ Influencer threads: Auto-created from current collaborations
- ✅ Idempotent thread creation - safe to run multiple times
- ✅ Removed manual thread creation endpoint (development UI only)
- ✅ Thread title format: "Campaign: {campaign_name}"
- ✅ Extracted `sync_user_campaign_threads()` function for reusability

**New Hyptrb Endpoints Integrated:**
- `GET /clients/get/all/campaigns/{email}` - Fetch all client campaigns
- `GET /influencer/get/clients/collaborations/{uid}` - Fetch influencer collaborations

**Campaign-Thread Mapping:**
- One thread per campaign per user (clients and influencers get separate threads)
- Threads are campaign-specific, not shared across users
- Thread lifecycle tied to Hyptrb campaign status
- Always kept in sync with Hyptrb on thread listing

### Version 2.3.0 - Thread Ownership & Auto-Participant (2025-10-12)
**Enhanced Thread Management**
- ✅ Threads now have explicit ownership (created_by user)
- ✅ Only thread owners can view and manage their threads
- ✅ Thread owner automatically added as participant1 in all conversations
- ✅ Simplified conversation creation - only requires `other_participant_id`
- ✅ GET /messages/threads now filters by authenticated user
- ✅ Added 403 Forbidden responses for unauthorized thread access
- ✅ Backward compatibility with `participant2_id` parameter

**Workflow Changes:**
- Creating a thread: User becomes the owner automatically
- Creating a conversation: Thread owner is participant1, request only needs other participant
- Accessing threads: Only owners can access their threads
- Conversations: Thread owner is always included

### Version 2.2.0 - Hyptrb API Integration (2025-10-12)
**Automatic Profile Enrichment**
- ✅ Integrated with Hyptrb API for automatic user profile fetching
- ✅ Auto-fetch user roles from `https://api.hyptrb.africa/roles/{email}`
- ✅ Auto-fetch profiles based on role (client/admin/influencer)
- ✅ Extract display names from business/profile data
- ✅ **Auto-use influencer avatars** from `profile_picture_url` field
- ✅ Conversations and messages automatically use database avatars
- ✅ Graceful fallback if Hyptrb API is unavailable
- ✅ Role field added to users table
- ✅ Comprehensive error handling for API failures

**Hyptrb Endpoints Integrated:**
- `GET /roles/{email}` - Fetch user role
- `GET /clients/get/{email}` - Fetch client profile (uses `businessName`)
- `GET /admin/profile/{email}` - Fetch admin profile (uses `name`)
- `GET /influencer/get/profile/{uid}` - Fetch influencer profile (uses `full_name`, `profile_picture_url`)

**Avatar Priority:**
1. Hyptrb API avatar (`profile_picture_url` for influencers)
2. Firebase user photo
3. Provided avatar in request
4. Empty string (no avatar)

### Version 2.1.0 - Access Control Fix (2025-10-11)
**Critical Security Update**
- ✅ Fixed conversation access control vulnerability
- ✅ Users can now only see conversations they're participants in
- ✅ Added participant verification for message operations
- ✅ Database-level filtering for conversations
- ✅ Returns 403 Forbidden for unauthorized access attempts
- ✅ Enhanced user search with autocomplete and multi-select

### Version 2.0.0 - Firebase Secured (2025-10-10)
**Major Security Update**
- ✅ Added Firebase Admin SDK authentication
- ✅ All endpoints now require valid Firebase ID tokens
- ✅ User context available in all authenticated requests
- ✅ Authorization checks (users can only delete own messages)
- ✅ Comprehensive security documentation

### Version 1.3.0 - Thread-Based Architecture
**Structural Improvements**
- ✅ Migrated to thread-based conversation model
- ✅ Threads organize conversations by campaign/topic
- ✅ Nested resource hierarchy (threads → conversations → messages)
- ✅ Enhanced database schema with triggers and indexes

### Version 1.2.0 - Multiple Attachments
**Feature Enhancements**
- ✅ Support for multiple file attachments per message
- ✅ Image dimension extraction (PIL)
- ✅ Video dimension extraction (OpenCV)
- ✅ Enhanced file metadata (size, type, dimensions)
- ✅ Backward compatibility with single attachments

### Version 1.1.0 - API Consolidation
**Design Improvements**
- ✅ Consolidated endpoints using proper HTTP methods
- ✅ RESTful design patterns
- ✅ Content-type detection for automatic routing
- ✅ 60% reduction in endpoint count

### Version 1.0.0 - Initial Release
**Core Features**
- ✅ Conversation-based messaging
- ✅ File attachments support
- ✅ SQLite database with migrations
- ✅ Soft delete for messages
- ✅ Read/unread status tracking

---

**Current Version:** 2.1.0 (Access Control Fixed)  
**Last Updated:** 2025-10-11  
**Status:** Production Ready ✅
