# meta developer: @ilyas_ugly

from .. import loader, utils
from telethon import types
from datetime import datetime, timedelta, timezone
import asyncio


@loader.tds
class UserActivityMod(loader.Module):
    """Shows last 5 messages from user with links and activity stats"""

    strings = {
        "name": "UserActivity",
        "no_args": "<b>❌ Provide username or reply to a message</b>",
        "processing": "<b>⏳ Processing...</b>",
        "error": "<b>❌ Error: {}</b>",
        "user_not_found": "<b>❌ User {} not found</b>",
        "no_messages": "<b>❌ No messages found from this user in this chat</b>",
        "activity_report": (
            "<b>👤 User Activity Report</b>\n\n"
            "<b>User:</b> {name}\n"
            "<b>Username:</b> {username}\n"
            "<b>ID:</b> <code>{user_id}</code>\n\n"
            "<b>📊 Statistics:</b>\n"
            "├ <b>Total messages:</b> {total_msgs}\n"
            "├ <b>Messages today:</b> {today_msgs}\n"
            "├ <b>Messages this week:</b> {week_msgs}\n"
            "├ <b>First message:</b> {first_msg_time}\n"
            "└ <b>Last message:</b> {last_msg_time}\n\n"
            "<b>📝 Last 5 messages:</b>\n{messages_list}"
        ),
        "message_item": "├ <a href='{link}'>{time}</a>: {text}\n",
        "message_item_last": "└ <a href='{link}'>{time}</a>: {text}\n",
    }

    @loader.command()
    async def useract(self, message):
        """<username/reply> - Show user activity and last 5 messages"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        
        if not args and not reply:
            await utils.answer(message, self.strings["no_args"])
            return
        
        status_msg = await utils.answer(message, self.strings["processing"])
        
        try:
            # Determine user
            if reply:
                user = await message.client.get_entity(reply.sender_id)
            else:
                username = args.strip().lstrip('@')
                try:
                    user = await message.client.get_entity(username)
                except Exception:
                    await utils.answer(message, self.strings["user_not_found"].format(username))
                    return
            
            # Get chat
            chat = await message.get_chat()
            chat_id = chat.id
            
            # Collect messages
            messages_list = []
            total_count = 0
            today_count = 0
            week_count = 0
            first_msg_date = None
            last_msg_date = None
            
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = now - timedelta(days=7)
            
            # Get last 5 messages for display
            async for msg in message.client.iter_messages(chat, from_user=user.id, limit=5):
                messages_list.append(msg)
            
            if not messages_list:
                await utils.answer(message, self.strings["no_messages"])
                return
            
            # Count all messages and get statistics
            async for msg in message.client.iter_messages(chat, from_user=user.id, limit=None):
                total_count += 1
                
                msg_date = msg.date.replace(tzinfo=timezone.utc) if msg.date.tzinfo is None else msg.date
                
                if msg_date >= today_start:
                    today_count += 1
                
                if msg_date >= week_start:
                    week_count += 1
                
                if first_msg_date is None or msg_date < first_msg_date:
                    first_msg_date = msg_date
                
                if last_msg_date is None or msg_date > last_msg_date:
                    last_msg_date = msg_date
            
            # Build messages list with links
            messages_text = ""
            for idx, msg in enumerate(messages_list):
                # Get message link
                if chat.username:
                    msg_link = f"https://t.me/{chat.username}/{msg.id}"
                else:
                    msg_link = f"https://t.me/c/{str(chat_id)[4:]}/{msg.id}"
                
                # Get message preview
                if msg.text:
                    text_preview = msg.text[:50] + "..." if len(msg.text) > 50 else msg.text
                    text_preview = text_preview.replace('\n', ' ')
                elif msg.media:
                    text_preview = "📎 Media"
                else:
                    text_preview = "Message"
                
                # Format time
                msg_time = msg.date.strftime("%d.%m.%Y %H:%M")
                
                # Add to list
                if idx == len(messages_list) - 1:
                    messages_text += self.strings["message_item_last"].format(
                        link=msg_link,
                        time=msg_time,
                        text=text_preview
                    )
                else:
                    messages_text += self.strings["message_item"].format(
                        link=msg_link,
                        time=msg_time,
                        text=text_preview
                    )
            
            # Format user info
            user_name = utils.escape_html(user.first_name or "Unknown")
            if user.last_name:
                user_name += " " + utils.escape_html(user.last_name)
            
            username_str = f"@{user.username}" if user.username else "None"
            
            # Format dates
            first_msg_str = first_msg_date.strftime("%d.%m.%Y %H:%M") if first_msg_date else "Unknown"
            last_msg_str = last_msg_date.strftime("%d.%m.%Y %H:%M") if last_msg_date else "Unknown"
            
            # Build final message
            report = self.strings["activity_report"].format(
                name=user_name,
                username=username_str,
                user_id=user.id,
                total_msgs=total_count,
                today_msgs=today_count,
                week_msgs=week_count,
                first_msg_time=first_msg_str,
                last_msg_time=last_msg_str,
                messages_list=messages_text
            )
            
            await utils.answer(status_msg, report)
            
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command()
    async def userlast(self, message):
        """<username/reply> [count] - Show last N messages with links (default 5)"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        
        if not args and not reply:
            await utils.answer(message, self.strings["no_args"])
            return
        
        status_msg = await utils.answer(message, self.strings["processing"])
        
        try:
            # Parse arguments
            count = 5
            if reply:
                user = await message.client.get_entity(reply.sender_id)
                if args and args.isdigit():
                    count = min(int(args), 50)
            else:
                parts = args.split()
                username = parts[0].lstrip('@')
                if len(parts) > 1 and parts[1].isdigit():
                    count = min(int(parts[1]), 50)
                
                try:
                    user = await message.client.get_entity(username)
                except Exception:
                    await utils.answer(message, self.strings["user_not_found"].format(username))
                    return
            
            # Get chat
            chat = await message.get_chat()
            chat_id = chat.id
            
            # Collect messages
            messages_list = []
            async for msg in message.client.iter_messages(chat, from_user=user.id, limit=count):
                messages_list.append(msg)
            
            if not messages_list:
                await utils.answer(message, self.strings["no_messages"])
                return
            
            # Build messages list
            user_name = utils.escape_html(user.first_name or "Unknown")
            result = f"<b>📝 Last {len(messages_list)} messages from {user_name}:</b>\n\n"
            
            for idx, msg in enumerate(messages_list):
                # Get message link
                if chat.username:
                    msg_link = f"https://t.me/{chat.username}/{msg.id}"
                else:
                    msg_link = f"https://t.me/c/{str(chat_id)[4:]}/{msg.id}"
                
                # Get message preview
                if msg.text:
                    text_preview = msg.text[:60] + "..." if len(msg.text) > 60 else msg.text
                    text_preview = text_preview.replace('\n', ' ')
                elif msg.media:
                    text_preview = "📎 Media"
                else:
                    text_preview = "Message"
                
                # Format time
                msg_time = msg.date.strftime("%d.%m %H:%M")
                
                # Add to list
                if idx == len(messages_list) - 1:
                    result += f"└ <a href='{msg_link}'>{msg_time}</a>: {text_preview}\n"
                else:
                    result += f"├ <a href='{msg_link}'>{msg_time}</a>: {text_preview}\n"
            
            await utils.answer(status_msg, result)
            
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))