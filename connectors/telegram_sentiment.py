# enhanced_telegram_monitor.py
from telethon import TelegramClient
from telethon.tl.types import Message, Channel
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
from datetime import datetime, timedelta

@dataclass
class EnhancedTelegramData:
    messages: List[str]
    member_count: int
    online_count: int
    message_frequency: float  # messages per hour
    active_users: int
    admin_activity: bool
    media_share_ratio: float

class EnhancedTelegramMonitor:
    def __init__(self, api_id: int, api_hash: str, bot_token: str):
        self.client = TelegramClient('bot_session', api_id, api_hash)
        self.bot_token = bot_token
        self.monitored_groups = {}  # {group_id: last_message_id}
        
    async def connect(self):
        """Connect using bot credentials"""
        await self.client.start(bot_token=self.bot_token)
        logger.info("🤖 Telegram Bot connected successfully")
    
    async def join_and_monitor_group(self, group_link: str) -> bool:
        """Join a group and start monitoring it"""
        try:
            # Join the group using invite link
            group_entity = await self.client.get_entity(group_link)
            await self.client.join_channel(group_entity)
            
            # Store for monitoring
            self.monitored_groups[group_entity.id] = 0
            logger.info(f"✅ Joined and monitoring group: {group_entity.title}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to join group {group_link}: {e}")
            return False
    
    async def scrape_private_group_messages(self, group_identifier, limit: int = 200) -> EnhancedTelegramData:
        """Scrape messages from private groups the bot has joined"""
        try:
            group_entity = await self.client.get_entity(group_identifier)
            
            # Get recent messages
            messages = []
            async for message in self.client.iter_messages(
                group_entity, 
                limit=limit,
                offset_date=datetime.now() - timedelta(hours=24)  # Last 24 hours only
            ):
                if message.text and message.text.strip():
                    messages.append({
                        'text': message.text,
                        'date': message.date,
                        'user_id': message.sender_id,
                        'is_admin': await self._is_admin(group_entity, message.sender_id)
                    })
            
            # Analyze group metrics
            group_metrics = await self._analyze_group_health(group_entity, messages)
            
            return EnhancedTelegramData(
                messages=[msg['text'] for msg in messages],
                member_count=group_metrics['member_count'],
                online_count=group_metrics['online_count'],
                message_frequency=group_metrics['message_frequency'],
                active_users=group_metrics['active_users'],
                admin_activity=group_metrics['admin_activity'],
                media_share_ratio=group_metrics['media_share_ratio']
            )
            
        except Exception as e:
            logger.error(f"❌ Error scraping private group {group_identifier}: {e}")
            return EnhancedTelegramData([], 0, 0, 0, 0, False, 0)
    
    async def _analyze_group_health(self, group_entity, messages: List) -> Dict:
        """Analyze group health metrics"""
        if not messages:
            return {
                'member_count': 0,
                'online_count': 0, 
                'message_frequency': 0,
                'active_users': 0,
                'admin_activity': False,
                'media_share_ratio': 0
            }
        
        # Get group info
        try:
            full_chat = await self.client.get_entity(group_entity)
            member_count = getattr(full_chat, 'participants_count', 0)
            online_count = getattr(full_chat, 'online_count', 0)
        except:
            member_count = online_count = 0
        
        # Calculate metrics
        time_span_hours = 24
        message_frequency = len(messages) / time_span_hours
        
        unique_users = len(set(msg['user_id'] for msg in messages))
        active_users = unique_users
        
        admin_activity = any(msg['is_admin'] for msg in messages)
        
        # Media share ratio (approximate)
        media_messages = sum(1 for msg in messages if any(media_indicator in msg['text'].lower() 
                                                         for media_indicator in ['http', '.com', 't.me']))
        media_share_ratio = media_messages / len(messages) if messages else 0
        
        return {
            'member_count': member_count,
            'online_count': online_count,
            'message_frequency': message_frequency,
            'active_users': active_users,
            'admin_activity': admin_activity,
            'media_share_ratio': media_share_ratio
        }
    
    async def _is_admin(self, group_entity, user_id) -> bool:
        """Check if user is admin in group"""
        try:
            participants = await self.client.get_participants(group_entity)
            for participant in participants:
                if participant.id == user_id:
                    return participant.admin_rights is not None
        except:
            pass
        return False