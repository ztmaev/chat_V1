import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  getThreads, 
  getConversations, 
  getMessages, 
  createThread as apiCreateThread,
  createConversation as apiCreateConversation,
  sendMessage as apiSendMessage,
  getAllUsers
} from '../api';
import { auth } from '../firebase';
import styles from './ThreadManagement.module.css';

interface Thread {
  id: string;
  title: string;
  description?: string;
  created_at: string;
  updated_at: string;
  status: string;
}

interface Conversation {
  id: string;
  thread_id: string;
  participant1_id: string;
  participant1_name: string;
  participant2_id: string;
  participant2_name: string;
  last_message?: string;
  last_message_time?: string;
  unread_count: number;
}

interface Message {
  id: string;
  content: string;
  sender_id: string;
  sender_name: string;
  timestamp: string;
}

interface User {
  firebase_uid: string;
  email: string;
  display_name: string;
  photo_url?: string;
  role?: string;
}

const ThreadManagement: React.FC = () => {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [selectedThread, setSelectedThread] = useState<Thread | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newThread, setNewThread] = useState({ title: '', description: '' });
  const [newConversation, setNewConversation] = useState({ name: '', selectedUserIds: [] as string[] });
  const [users, setUsers] = useState<User[]>([]);
  const [showCreateConversation, setShowCreateConversation] = useState(false);
  const [userSearchQuery, setUserSearchQuery] = useState('');
  const [showUserSuggestions, setShowUserSuggestions] = useState(false);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState({
    threads: false,
    conversations: false,
    messages: false,
    users: false
  });
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const currentUser = auth.currentUser;
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Load all threads
  useEffect(() => {
    const fetchThreads = async () => {
      try {
        setLoading(prev => ({ ...prev, threads: true }));
        const data = await getThreads();
        setThreads(data.threads || []);
      } catch (err) {
        setError('Failed to load threads');
        console.error('Error loading threads:', err);
      } finally {
        setLoading(prev => ({ ...prev, threads: false }));
      }
    };

    fetchThreads();
  }, []);

  // Load all users
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoading(prev => ({ ...prev, users: true }));
        const data = await getAllUsers();
        setUsers(data.users || []);
      } catch (err) {
        console.error('Error loading users:', err);
      } finally {
        setLoading(prev => ({ ...prev, users: false }));
      }
    };

    fetchUsers();
  }, []);

  // Load conversations when a thread is selected
  useEffect(() => {
    if (selectedThread) {
      const fetchConversations = async () => {
        try {
          setLoading(prev => ({ ...prev, conversations: true }));
          const data = await getConversations(selectedThread.id);
          setConversations(data.conversations || []);
        } catch (err) {
          setError('Failed to load conversations');
          console.error('Error loading conversations:', err);
        } finally {
          setLoading(prev => ({ ...prev, conversations: false }));
        }
      };

      fetchConversations();
    }
  }, [selectedThread]);

  // Load messages when a conversation is selected
  useEffect(() => {
    if (selectedThread && selectedConversation) {
      const fetchMessages = async () => {
        try {
          setLoading(prev => ({ ...prev, messages: true }));
          const data = await getMessages(selectedThread.id, selectedConversation.id);
          setMessages(data.messages || []);
        } catch (err) {
          setError('Failed to load messages');
          console.error('Error loading messages:', err);
        } finally {
          setLoading(prev => ({ ...prev, messages: false }));
        }
      };

      fetchMessages();
    }
  }, [selectedConversation]);

  const handleCreateThread = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newThread.title.trim()) return;

    try {
      const thread = await apiCreateThread({
        title: newThread.title,
        description: newThread.description
      });
      
      setThreads(prev => [...prev, thread]);
      setNewThread({ title: '', description: '' });
    } catch (err) {
      setError('Failed to create thread');
      console.error('Error creating thread:', err);
    }
  };

  const handleCreateConversation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newConversation.name.trim() || newConversation.selectedUserIds.length === 0 || !selectedThread || !currentUser) {
      setError('Please provide a conversation name and select at least one user');
      return;
    }

    try {
      // For now, create conversation with first selected user (can be enhanced for group chats)
      const selectedUserId = newConversation.selectedUserIds[0];
      const selectedUser = users.find(u => u.firebase_uid === selectedUserId);
      if (!selectedUser) {
        setError('Selected user not found');
        return;
      }

      const conversationData = {
        participant1_id: currentUser.uid,
        participant1_name: currentUser.displayName || currentUser.email || 'You',
        participant1_avatar: currentUser.photoURL || '',
        participant2_id: selectedUser.firebase_uid,
        participant2_name: selectedUser.display_name,
        participant2_avatar: selectedUser.photo_url || ''
      };

      const result = await apiCreateConversation(selectedThread.id, conversationData);
      
      // Refresh conversations
      const data = await getConversations(selectedThread.id);
      setConversations(data.conversations || []);
      
      setNewConversation({ name: '', selectedUserIds: [] });
      setUserSearchQuery('');
      setShowCreateConversation(false);
      setError('');
    } catch (err) {
      setError('Failed to create conversation');
      console.error('Error creating conversation:', err);
    }
  };

  const handleAddUser = (userId: string) => {
    if (!newConversation.selectedUserIds.includes(userId)) {
      setNewConversation({
        ...newConversation,
        selectedUserIds: [...newConversation.selectedUserIds, userId]
      });
    }
    setUserSearchQuery('');
    setShowUserSuggestions(false);
  };

  const handleRemoveUser = (userId: string) => {
    setNewConversation({
      ...newConversation,
      selectedUserIds: newConversation.selectedUserIds.filter(id => id !== userId)
    });
  };

  const filteredUsers = users.filter(user => {
    const searchLower = userSearchQuery.toLowerCase();
    return (
      user.display_name.toLowerCase().includes(searchLower) ||
      user.email.toLowerCase().includes(searchLower)
    ) && !newConversation.selectedUserIds.includes(user.firebase_uid);
  });

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target as Node)) {
        setShowUserSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedThread || !selectedConversation || !currentUser) return;

    try {
      const message = await apiSendMessage(
        selectedThread.id,
        selectedConversation.id,
        newMessage
      );
      
      setMessages(prev => [...prev, {
        ...message,
        sender_id: currentUser.uid,
        sender_name: currentUser.displayName || 'You'
      }]);
      
      setNewMessage('');
    } catch (err) {
      setError('Failed to send message');
      console.error('Error sending message:', err);
    }
  };

  if (!currentUser) {
    return <div>Please log in to manage threads</div>;
  }

  return (
    <div className={styles['thread-management']}>
      <h1>Thread Management</h1>
      
      {error && <div className={styles.error}>{error}</div>}
      
      <div className={styles['thread-layout']}>
        {/* Thread List */}
        <div className={styles['thread-list']}>
          <h2>Threads</h2>
          <form onSubmit={handleCreateThread} className={styles['thread-form']}>
            <input
              type="text"
              placeholder="Thread Title"
              value={newThread.title}
              onChange={(e) => setNewThread({...newThread, title: e.target.value})}
              required
            />
            <textarea
              placeholder="Description (optional)"
              value={newThread.description || ''}
              onChange={(e) => setNewThread({...newThread, description: e.target.value})}
            />
            <button type="submit" disabled={loading.threads}>
              {loading.threads ? 'Creating...' : 'Create Thread'}
            </button>
          </form>
          
          {loading.threads ? (
            <div>Loading threads...</div>
          ) : (
            <ul className={styles['threads-list']}>
              {threads.map(thread => (
                <li 
                  key={thread.id}
                  className={`${styles['thread-item']} ${selectedThread?.id === thread.id ? styles.active : ''}`}
                  onClick={() => setSelectedThread(thread)}
                >
                  <h3>{thread.title}</h3>
                  {thread.description && <p>{thread.description}</p>}
                  <small>Last updated: {new Date(thread.updated_at).toLocaleString()}</small>
                </li>
              ))}
            </ul>
          )}
        </div>
        
        {/* Conversation List */}
        <div className={styles['conversation-list']}>
          <h2>Conversations</h2>
          {!selectedThread ? (
            <p>Select a thread to view conversations</p>
          ) : (
            <>
              <button 
                className={styles['create-conversation-btn']}
                onClick={() => setShowCreateConversation(!showCreateConversation)}
                disabled={loading.users}
              >
                {showCreateConversation ? 'Cancel' : '+ New Conversation'}
              </button>

              {showCreateConversation && (
                <form onSubmit={handleCreateConversation} className={styles['conversation-form']}>
                  <input
                    type="text"
                    placeholder="Conversation Name"
                    value={newConversation.name}
                    onChange={(e) => setNewConversation({...newConversation, name: e.target.value})}
                    required
                  />
                  
                  {/* Selected Users */}
                  {newConversation.selectedUserIds.length > 0 && (
                    <div className={styles['selected-users']}>
                      {newConversation.selectedUserIds.map(userId => {
                        const user = users.find(u => u.firebase_uid === userId);
                        if (!user) return null;
                        return (
                          <div key={userId} className={styles['selected-user-tag']}>
                            <span>
                              {user.display_name}
                              {user.firebase_uid === currentUser?.uid ? ' (You)' : ''}
                            </span>
                            <button
                              type="button"
                              onClick={() => handleRemoveUser(userId)}
                              className={styles['remove-user-btn']}
                            >
                              ×
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* User Search Field */}
                  <div className={styles['user-search-container']} ref={searchContainerRef}>
                    <input
                      type="text"
                      placeholder="Search users by name or email..."
                      value={userSearchQuery}
                      onChange={(e) => {
                        setUserSearchQuery(e.target.value);
                        setShowUserSuggestions(true);
                      }}
                      onFocus={() => setShowUserSuggestions(true)}
                      disabled={users.length === 0}
                      className={styles['user-search-input']}
                    />
                    
                    {/* User Suggestions Dropdown */}
                    {showUserSuggestions && userSearchQuery && filteredUsers.length > 0 && (
                      <div className={styles['user-suggestions']}>
                        {filteredUsers.slice(0, 5).map(user => (
                          <div
                            key={user.firebase_uid}
                            className={styles['user-suggestion-item']}
                            onClick={() => handleAddUser(user.firebase_uid)}
                          >
                            <div className={styles['user-info']}>
                              <div className={styles['user-name']}>
                                {user.display_name}
                                {user.firebase_uid === currentUser?.uid && (
                                  <span className={styles['you-badge']}>(You)</span>
                                )}
                              </div>
                              <div className={styles['user-email']}>{user.email}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {showUserSuggestions && userSearchQuery && filteredUsers.length === 0 && (
                      <div className={styles['user-suggestions']}>
                        <div className={styles['no-results']}>No users found</div>
                      </div>
                    )}
                  </div>

                  <button type="submit" disabled={loading.conversations || newConversation.selectedUserIds.length === 0}>
                    {loading.conversations ? 'Creating...' : 'Create'}
                  </button>
                  
                  {users.length === 0 && (
                    <p className={styles['no-users-message']}>
                      ℹ️ No users available. Please check your database connection.
                    </p>
                  )}
                </form>
              )}

              {loading.conversations ? (
                <div>Loading conversations...</div>
              ) : (
                <ul className={styles['conversations-list']}>
                  {conversations.map(conv => (
                    <li 
                      key={conv.id}
                      className={`${styles['conversation-item']} ${selectedConversation?.id === conv.id ? styles.active : ''}`}
                      onClick={() => setSelectedConversation(conv)}
                    >
                      <h3>
                        {conv.participant1_id === currentUser?.uid 
                          ? conv.participant2_name 
                          : conv.participant1_name}
                      </h3>
                      {conv.last_message && (
                        <p className={styles['last-message']}>
                          {conv.last_message.length > 50 
                            ? `${conv.last_message.substring(0, 50)}...` 
                            : conv.last_message}
                        </p>
                      )}
                      {conv.unread_count > 0 && (
                        <span className={styles['unread-badge']}>{conv.unread_count}</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
        
        {/* Message Area */}
        <div className={styles['message-area']}>
          {!selectedConversation ? (
            <p>Select a conversation to view messages</p>
          ) : (
            <>
              <div className={styles['message-header']}>
                <h2>
                  {selectedConversation.participant1_id === currentUser?.uid
                    ? selectedConversation.participant2_name
                    : selectedConversation.participant1_name}
                </h2>
              </div>
              
              <div className={styles.messages}>
                {loading.messages ? (
                  <div>Loading messages...</div>
                ) : messages.length === 0 ? (
                  <div className={styles['no-messages']}>No messages yet. Start the conversation!</div>
                ) : (
                  messages.map(message => (
                    <div 
                      key={message.id} 
                      className={`${styles.message} ${message.sender_id === currentUser?.uid ? styles.sent : styles.received}`}
                    >
                      <div className={styles['message-sender']}>
                        {message.sender_id === currentUser?.uid ? 'You' : message.sender_name}
                      </div>
                      <div className={styles['message-content']}>{message.content}</div>
                      <div className={styles['message-time']}>
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  ))
                )}
              </div>
              
              <form onSubmit={handleSendMessage} className={styles['message-form']}>
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder="Type a message..."
                  disabled={loading.messages}
                />
                <button type="submit" disabled={!newMessage.trim() || loading.messages}>
                  {loading.messages ? 'Sending...' : 'Send'}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ThreadManagement;
