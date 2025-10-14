import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { auth } from './firebase';
import { signInWithEmailAndPassword, signOut, User } from 'firebase/auth';
import { getThreads, getConversations, getMessages, sendMessage, testAuth } from './api';
import ThreadManagement from './pages/ThreadManagement';
import './App.css';

interface Thread {
  id: string;
  title: string;
  description: string;
}

interface Conversation {
  id: string;
  participant1_name: string;
  participant2_name: string;
  last_message: string;
  unread_count: number;
}

interface Message {
  id: string;
  sender_name: string;
  content: string;
  timestamp: string;
  deleted: boolean;
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [threads, setThreads] = useState<Thread[]>([]);
  const [selectedThread, setSelectedThread] = useState<Thread | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged((user) => {
      setUser(user);
      if (user) {
        loadThreads();
      }
    });
    return unsubscribe;
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      await signInWithEmailAndPassword(auth, email, password);
      // Test authentication
      const authTest = await testAuth();
      console.log('Auth test:', authTest);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await signOut(auth);
    setThreads([]);
    setConversations([]);
    setMessages([]);
    setSelectedThread(null);
    setSelectedConversation(null);
  };

  const loadThreads = async () => {
    try {
      const data = await getThreads();
      setThreads(data.threads || []);
    } catch (err: any) {
      console.error('Failed to load threads:', err);
      setError(err.message);
    }
  };

  const loadConversations = async (thread: Thread) => {
    try {
      setSelectedThread(thread);
      const data = await getConversations(thread.id);
      setConversations(data.conversations || []);
      setSelectedConversation(null);
      setMessages([]);
    } catch (err: any) {
      console.error('Failed to load conversations:', err);
      setError(err.message);
    }
  };

  const loadMessages = async (conversation: Conversation) => {
    if (!selectedThread) return;
    
    try {
      setSelectedConversation(conversation);
      const data = await getMessages(selectedThread.id, conversation.id);
      setMessages(data.messages || []);
    } catch (err: any) {
      console.error('Failed to load messages:', err);
      setError(err.message);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedThread || !selectedConversation || !newMessage.trim()) return;
    
    try {
      await sendMessage(selectedThread.id, selectedConversation.id, newMessage);
      setNewMessage('');
      // Reload messages
      loadMessages(selectedConversation);
    } catch (err: any) {
      console.error('Failed to send message:', err);
      setError(err.message);
    }
  };

  return (
    <Router>
      <div className="app">
        {!user ? (
          <div className="login-container">
            <h1>Chat API Demo</h1>
            {error && <div className="error">{error}</div>}
            <form onSubmit={handleLogin} className="login-form">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email"
                required
              />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                required
              />
              <button type="submit" disabled={loading}>
                {loading ? 'Logging in...' : 'Login'}
              </button>
            </form>
          </div>
        ) : (
          <Routes>
            <Route path="/" element={<Navigate to="/threads" replace />} />
            <Route
              path="/threads/*"
              element={
                <div className="app-container">
                  <header className="app-header">
                    <h1>Chat API Demo</h1>
                    <button onClick={handleLogout} className="logout-btn">
                      Logout
                    </button>
                  </header>
                  <ThreadManagement />
                </div>
              }
            />
          </Routes>
        )}
      </div>
    </Router>
  );
}

export default App;
