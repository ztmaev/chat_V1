# Chat API Demo UI

Simple React frontend to test the Firebase-secured Chat API.

## Features

- 🔐 Firebase Authentication
- 💬 Thread-based messaging
- 📁 View conversations
- ✉️ Send messages
- 🎨 Modern dark theme UI

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Copy environment file
cp .env.example .env

# 3. Start development server
npm run dev
```

The app will be available at `http://localhost:3000`

## Prerequisites

- Node.js 16+
- npm or yarn
- Running Chat API on `http://localhost:5001`
- Firebase project with Authentication enabled

## Environment Variables

Create `.env` file from `.env.example`:

```env
VITE_FIREBASE_API_KEY=your-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
VITE_FIREBASE_APP_ID=your-app-id
VITE_FIREBASE_MEASUREMENT_ID=your-measurement-id
VITE_API_URL=http://localhost:5001
```

## Usage

### 1. Start the Chat API

```bash
cd ../
python3 app.py
```

### 2. Create Firebase User

Create a test user in your Firebase Console:
- Go to Authentication → Users
- Add user with email/password

### 3. Login to Demo UI

Use the Firebase credentials to login and test the API.

## Features

### Authentication
- Firebase email/password login
- Automatic token refresh
- Secure API calls with Bearer tokens

### Messaging
- View all threads
- Browse conversations in threads
- Read messages
- Send new messages
- Real-time updates

### UI/UX
- Modern dark theme
- Responsive design
- Loading states
- Error handling
- Empty states

## Project Structure

```
chat_api_demo_ui/
├── src/
│   ├── App.tsx           # Main application component
│   ├── App.css           # Styling
│   ├── firebase.ts       # Firebase configuration
│   ├── api.ts            # API functions
│   ├── main.tsx          # Entry point
│   └── vite-env.d.ts     # TypeScript definitions
├── index.html            # HTML template
├── package.json          # Dependencies
├── vite.config.ts        # Vite configuration
├── tsconfig.json         # TypeScript config
└── .env.example          # Environment template
```

## API Integration

The app integrates with these Chat API endpoints:

- `GET /auth/test` - Test authentication
- `GET /messages/threads` - List threads
- `GET /messages/threads/{id}/conversations` - List conversations
- `GET /messages/threads/{id}/conversations/{id}` - Get messages
- `POST /messages/threads/{id}/conversations/{id}` - Send message

## Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Technologies

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Firebase** - Authentication
- **Fetch API** - HTTP requests

## Troubleshooting

### "User not authenticated" error
- Make sure you're logged in with valid Firebase credentials
- Check that Firebase config in `.env` is correct

### "Failed to fetch" error
- Ensure Chat API is running on `http://localhost:5001`
- Check CORS is enabled in the API
- Verify `VITE_API_URL` in `.env`

### "401 Unauthorized" error
- Firebase ID token may have expired
- Try logging out and logging back in
- Check that API has correct Firebase service account key

## Notes

- This is a demo/testing UI, not production-ready
- Designed to test the Chat API functionality
- Uses the same Firebase project as the main app
- Tokens expire after 1 hour (automatic refresh)

## License

Part of the InfluencerConnect project.
