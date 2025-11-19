# Participant Type Field Implementation

## Overview
Added `participant2_email` and `participant_type` fields to the conversations table to properly track whether a participant is a client or influencer.

## Database Changes

### New Columns in `conversations` table:
- `participant2_email TEXT` - Stores the email address of participant2 (useful for identifying clients)
- `participant_type TEXT` - Stores the type of participant2: 'client' or 'influencer'

## Backend Changes

### 1. Database Schema (`db.py`)
- Updated `CREATE TABLE conversations` statement to include new columns
- Updated `get_or_create_conversation()` method to accept and store these fields

### 2. API Endpoint (`app.py`)
- Updated `POST /messages/threads/<thread_id>/conversations` endpoint
- Now accepts `participant2_email` and `participant_type` in request body
- Passes these values to the database layer

## Frontend Integration

The frontend (`AdminMessages.tsx`) already sends these fields when creating conversations:

```typescript
const conversationData = {
  other_participant_id: participant.id,
  participant2_id: participant.id,
  name: conversationName,
  participant2_name: participant.name,
  participant2_avatar: undefined,
  participant2_email: participant.email,  // ✓ Sent
  participant_type: participant.type      // ✓ Sent ('client' or 'influencer')
};
```

## Migration

For existing databases, run:

```bash
python migrate_add_participant_fields.py
```

This script:
- Adds the new columns if they don't exist
- Is idempotent (safe to run multiple times)
- Shows statistics about conversations needing type inference

## Benefits

1. **No More Flickering**: Labels show correctly on first render
2. **Persistent Data**: Type is stored in database, not just localStorage
3. **Cleaner Code**: No complex heuristics needed to infer participant type
4. **Backend-First**: Single source of truth in the database

## API Request Example

```bash
POST /messages/threads/t12345/conversations
{
  "other_participant_id": "firebase_uid_123",
  "participant2_name": "John Doe",
  "participant2_email": "john@example.com",
  "participant_type": "client",
  "name": "Campaign Discussion"
}
```

## API Response

The conversation object now includes:

```json
{
  "id": "c1234abcd",
  "thread_id": "t12345",
  "participant1_id": "admin_uid",
  "participant1_name": "Admin",
  "participant2_id": "firebase_uid_123",
  "participant2_name": "John Doe",
  "participant2_email": "john@example.com",
  "participant_type": "client",
  "created_at": "2024-01-01T12:00:00",
  ...
}
```

## Backward Compatibility

- Existing conversations without `participant_type` will have NULL value
- Frontend handles NULL gracefully with fallback logic
- Migration script can be enhanced to infer types for existing conversations

## Next Steps

To fully migrate existing conversations, you can:

1. Add logic to the migration script to infer `participant_type` based on:
   - Presence of email in `participant2_id` (if email format → client)
   - Campaign data (match participant email with campaign client email)
   - Firebase UID patterns (UID without email → likely influencer)

2. Update existing conversations via SQL:
   ```sql
   -- Mark conversations with email addresses as clients
   UPDATE conversations 
   SET participant_type = 'client' 
   WHERE participant2_id LIKE '%@%' AND participant_type IS NULL;
   
   -- Remaining conversations are likely influencers
   UPDATE conversations 
   SET participant_type = 'influencer' 
   WHERE participant_type IS NULL;
   ```

