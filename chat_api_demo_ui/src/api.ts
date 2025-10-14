import { auth } from './firebase';

const API_URL = import.meta.env.VITE_API_URL || 'http://143.110.171.72:5001';

async function getAuthHeaders(): Promise<HeadersInit> {
  const user = auth.currentUser;
  if (!user) {
    throw new Error('User not authenticated');
  }
  
  const idToken = await user.getIdToken();
  
  return {
    'Authorization': `Bearer ${idToken}`,
  };
}

export async function apiCall(endpoint: string, options: RequestInit = {}) {
  const authHeaders = await getAuthHeaders();
  
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      ...options.headers,
      ...authHeaders,
    },
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Request failed' }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }
  
  return response.json();
}

// API functions
export async function createThread(threadData: { title: string; description?: string }) {
  return apiCall('/messages/threads', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(threadData),
  });
}

export async function getThreads() {
  return apiCall('/messages/threads');
}

export async function getThread(threadId: string) {
  return apiCall(`/messages/threads/${threadId}`);
}

export async function getConversations(threadId: string) {
  return apiCall(`/messages/threads/${threadId}/conversations`);
}

export async function getMessages(threadId: string, conversationId: string) {
  return apiCall(`/messages/threads/${threadId}/conversations/${conversationId}`);
}

export async function sendMessage(threadId: string, conversationId: string, content: string) {
  return apiCall(`/messages/threads/${threadId}/conversations/${conversationId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
}

export async function deleteMessage(threadId: string, conversationId: string, messageId: string) {
  return apiCall(`/messages/threads/${threadId}/conversations/${conversationId}/${messageId}`, {
    method: 'DELETE',
  });
}

export async function markAsRead(threadId: string, conversationId: string) {
  return apiCall(`/messages/threads/${threadId}/conversations/${conversationId}`, {
    method: 'PUT',
  });
}

export async function testAuth() {
  return apiCall('/auth/test');
}

// User management functions
export async function getAllUsers() {
  return apiCall('/users');
}

export async function getCurrentUser() {
  return apiCall('/users/me');
}

export async function getUserById(firebaseUid: string) {
  return apiCall(`/users/${firebaseUid}`);
}

// Create conversation function
export async function createConversation(
  threadId: string,
  conversationData: {
    participant1_id: string;
    participant1_name: string;
    participant1_avatar?: string;
    participant2_id: string;
    participant2_name: string;
    participant2_avatar?: string;
  }
) {
  return apiCall(`/messages/threads/${threadId}/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(conversationData),
  });
}
