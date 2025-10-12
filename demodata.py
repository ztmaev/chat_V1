"""
Demo data for messaging/chat API with threads
"""

# Sample threads
threads = [
    {
        'id': 't1',
        'title': 'Summer Campaign 2025',
        'description': 'Discussion thread for summer campaign collaboration',
        'created_by': 'client_1',
        'status': 'active'
    },
    {
        'id': 't2',
        'title': 'Product Launch Q3',
        'description': 'Coordination for Q3 product launch with influencers',
        'created_by': 'client_1',
        'status': 'active'
    }
]

# Sample conversations (within threads)
conversations = [
    {
        'id': 'c1',
        'thread_id': 't1',
        'participant1_id': 'client_1',
        'participant1_name': 'Marketing Team',
        'participant1_avatar': 'https://randomuser.me/api/portraits/lego/1.jpg',
        'participant2_id': 'inf_1',
        'participant2_name': 'Sarah Johnson',
        'participant2_avatar': 'https://randomuser.me/api/portraits/women/32.jpg',
        'last_message': 'Sounds great! Looking forward to it.',
        'last_message_time': '2025-08-28T14:30:00Z',
        'unread_count': 2,
        'status': 'active'
    },
    {
        'id': 'c2',
        'thread_id': 't1',
        'participant1_id': 'client_1',
        'participant1_name': 'Marketing Team',
        'participant1_avatar': 'https://randomuser.me/api/portraits/lego/1.jpg',
        'participant2_id': 'inf_2',
        'participant2_name': 'Mike Chen',
        'participant2_avatar': 'https://randomuser.me/api/portraits/men/45.jpg',
        'last_message': 'I can start next week',
        'last_message_time': '2025-08-27T16:45:00Z',
        'unread_count': 0,
        'status': 'active'
    },
    {
        'id': 'c3',
        'thread_id': 't2',
        'participant1_id': 'client_1',
        'participant1_name': 'Marketing Team',
        'participant1_avatar': 'https://randomuser.me/api/portraits/lego/1.jpg',
        'participant2_id': 'inf_3',
        'participant2_name': 'Jessica Lee',
        'participant2_avatar': 'https://randomuser.me/api/portraits/women/28.jpg',
        'last_message': 'Thanks for the quick payment!',
        'last_message_time': '2025-08-26T10:20:00Z',
        'unread_count': 0,
        'status': 'active'
    }
]

# Sample messages
messages = [
    {
        'id': 'm1',
        'conversation_id': 'c1',
        'thread_id': 't1',
        'sender_id': 'client_1',
        'sender_type': 'client',
        'sender_name': 'Marketing Team',
        'type': 'text',
        'content': 'Hi Sarah, we would love to collaborate with you on our summer campaign!',
        'text_content': 'Hi Sarah, we would love to collaborate with you on our summer campaign!',
        'timestamp': '2025-08-28T14:00:00Z',
        'status': 'delivered',
        'has_attachment': False
    },
    {
        'id': 'm2',
        'conversation_id': 'c1',
        'thread_id': 't1',
        'sender_id': 'inf_1',
        'sender_type': 'influencer',
        'sender_name': 'Sarah Johnson',
        'type': 'text',
        'content': 'Thank you so much! I would be honored to work with you.',
        'text_content': 'Thank you so much! I would be honored to work with you.',
        'timestamp': '2025-08-28T14:15:00Z',
        'status': 'delivered',
        'has_attachment': False
    },
    {
        'id': 'm3',
        'conversation_id': 'c1',
        'thread_id': 't1',
        'sender_id': 'client_1',
        'sender_type': 'client',
        'sender_name': 'Marketing Team',
        'type': 'text',
        'content': 'Great! Let me send you the campaign brief.',
        'text_content': 'Great! Let me send you the campaign brief.',
        'timestamp': '2025-08-28T14:20:00Z',
        'status': 'delivered',
        'has_attachment': False
    },
    {
        'id': 'm4',
        'conversation_id': 'c1',
        'thread_id': 't1',
        'sender_id': 'inf_1',
        'sender_type': 'influencer',
        'sender_name': 'Sarah Johnson',
        'type': 'text',
        'content': 'Sounds great! Looking forward to it.',
        'text_content': 'Sounds great! Looking forward to it.',
        'timestamp': '2025-08-28T14:30:00Z',
        'status': 'delivered',
        'has_attachment': False
    },
    {
        'id': 'm5',
        'conversation_id': 'c2',
        'thread_id': 't1',
        'sender_id': 'client_1',
        'sender_type': 'client',
        'sender_name': 'Marketing Team',
        'type': 'text',
        'content': 'Hey Mike, are you available for our summer campaign?',
        'text_content': 'Hey Mike, are you available for our summer campaign?',
        'timestamp': '2025-08-27T16:00:00Z',
        'status': 'delivered',
        'has_attachment': False
    },
    {
        'id': 'm6',
        'conversation_id': 'c2',
        'thread_id': 't1',
        'sender_id': 'inf_2',
        'sender_type': 'influencer',
        'sender_name': 'Mike Chen',
        'type': 'text',
        'content': 'I can start next week',
        'text_content': 'I can start next week',
        'timestamp': '2025-08-27T16:45:00Z',
        'status': 'delivered',
        'has_attachment': False
    },
    {
        'id': 'm7',
        'conversation_id': 'c3',
        'thread_id': 't2',
        'sender_id': 'client_1',
        'sender_type': 'client',
        'sender_name': 'Marketing Team',
        'type': 'text',
        'content': 'The product launch campaign results look amazing!',
        'text_content': 'The product launch campaign results look amazing!',
        'timestamp': '2025-08-26T10:00:00Z',
        'status': 'delivered',
        'has_attachment': False
    },
    {
        'id': 'm8',
        'conversation_id': 'c3',
        'thread_id': 't2',
        'sender_id': 'inf_3',
        'sender_type': 'influencer',
        'sender_name': 'Jessica Lee',
        'type': 'text',
        'content': 'Thanks for the quick payment!',
        'text_content': 'Thanks for the quick payment!',
        'timestamp': '2025-08-26T10:20:00Z',
        'status': 'delivered',
        'has_attachment': False
    }
]

messaging_data = {
    'threads': threads,
    'conversations': conversations,
    'messages': messages
}
