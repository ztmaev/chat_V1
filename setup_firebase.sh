#!/bin/bash

# Firebase Authentication Setup Script for Chat API
# This script helps set up Firebase authentication for the messaging API

set -e  # Exit on error

echo "🔥 Firebase Chat API Setup"
echo "=========================="
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo ""

# Check if pip is installed
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo "❌ pip is not installed. Please install pip."
    exit 1
fi

echo "✅ pip found"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Check for service account key
if [ -f "serviceAccountKey.json" ]; then
    echo "✅ Firebase service account key found: serviceAccountKey.json"
    echo ""
else
    echo "⚠️  Firebase service account key NOT found"
    echo ""
    echo "To complete setup, you need to:"
    echo "1. Go to Firebase Console: https://console.firebase.google.com/"
    echo "2. Select your project"
    echo "3. Go to Project Settings → Service Accounts"
    echo "4. Click 'Generate New Private Key'"
    echo "5. Save the JSON file as 'serviceAccountKey.json' in this directory"
    echo ""
    echo "Or set the FIREBASE_SERVICE_ACCOUNT_JSON environment variable with the JSON content."
    echo ""
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please update it with your configuration."
    echo ""
else
    echo "✅ .env file already exists"
    echo ""
fi

# Create uploads directory if it doesn't exist
if [ ! -d "uploads" ]; then
    echo "📁 Creating uploads directory..."
    mkdir -p uploads
    touch uploads/.gitkeep
    echo "✅ Uploads directory created"
else
    echo "✅ Uploads directory already exists"
fi
echo ""

# Check if database exists
if [ -f "messaging.db" ]; then
    echo "✅ Database found: messaging.db"
else
    echo "⚠️  Database not found. It will be created on first run."
fi
echo ""

echo "🎉 Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Ensure serviceAccountKey.json is in this directory"
echo "2. Update .env file if needed"
echo "3. Run the secure API:"
echo ""
echo "   source .venv/bin/activate"
echo "   python3 app_secure.py"
echo ""
echo "Or to replace the original app.py:"
echo ""
echo "   mv app.py app_insecure.py"
echo "   mv app_secure.py app.py"
echo "   python3 app.py"
echo ""
echo "📚 For detailed documentation, see FIREBASE_SETUP.md"
echo ""
