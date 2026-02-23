```python
# meta developer: @ilyas_ugly

from .. import loader, utils
from telethon import events, types
import re


@loader.tds
class VoresMod(loader.Module):
    """Auto-copies posts from Bedrock_RP channel with custom promotion"""

    strings = {
        "name": "Vores",
        "no_channel": "<b>❌ Provide channel link to forward posts to</b>",
        "invalid_channel": "<b>❌ Invalid channel link or username</b>",
        "started": "<b>✅ Auto-forwarding enabled</b>\nFrom: <code>@Bedrock_RP</code>\nTo: <code>{}</code>",
        "stopped": "<b>❌ Auto-forwarding disabled</b>",
        "status": "<b>ℹ️ Auto-forwarding status:</b>\nEnabled: <code>{}</code>\nTarget channel: <code>{}</code>",
        "error": "<b>❌ Error: {}</b>",
        "promo_text": "\n\n🔥 Лучший канал по ресурс пакам — <a href='https://t.me/{}'>{}</a>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "source_channel",
                "Bedrock_RP",
                lambda: "Source channel username (default: Bedrock_RP)",
            ),
            loader.ConfigValue(
                "exclude_mentions",
                True,
                lambda: "Exclude posts that mention @Bedrock_RP creator",
            ),
        )

    async def client_ready(self, client, db):
        self.db = db
        self._client = client
        self._enabled = self.db.get(self.strings["name"], "enabled", False)
        self._target_channel = self.db.get(self.strings["name"], "target_channel", None)
        self._target_name = self.db.get(self.strings["name"], "target_name", None)

    @loader.command()
    async def vores(self, message):
        """<channel_link> - Start auto-forwarding from Bedrock_RP to specified channel"""
        args = utils.get_args_raw(message)
        
        if not args:
            await utils.answer(message, self.strings["no_channel"])
            return
        
        try:
            # Parse channel link/username
            channel_username = args.strip()
            if "t.me/" in channel_username:
                channel_username = channel_username.split("t.me/")[-1].strip("/")
            channel_username = channel_username.lstrip("@")
            
            # Get target channel entity
            try:
                target_channel = await message.client.get_entity(channel_username)
            except Exception:
                await utils.answer(message, self.strings["invalid_channel"])
                return
            
            # Save settings
            self._enabled = True
            self._target_channel = channel_username
            self._target_name = getattr(target_channel, "title", channel_username)
            
            self.db.set(self.strings["name"], "enabled", True)
            self.db.set(self.strings["name"], "target_channel", channel_username)
            self.db.set(self.strings["name"], "target_name", self._target_name)
            
            await utils.answer(
                message,
                self.strings["started"].format(f"@{channel_username}")
            )
            
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    @loader.command()
    async def vorestop(self, message):
        """Stop auto-forwarding"""
        self._enabled = False
        self.db.set(self.strings["name"], "enabled", False)
        
        await utils.answer(message, self.strings["stopped"])

    @loader.command()
    async def vorestatus(self, message):
        """Check auto-forwarding status"""
        status = "Yes ✅" if self._enabled else "No ❌"
        target = self._target_channel if self._target_channel else "Not set"
        
        await utils.answer(
            message,
            self.strings["status"].format(status, target)
        )

    async def watcher(self, message):
        """Watch for new messages in source channel"""
        if not self._enabled or not self._target_channel:
            return
        
        # Check if message is from source channel
        if not message.chat:
            return
        
        chat_username = getattr(message.chat, "username", None)
        if chat_username != self.config["source_channel"]:
            return
        
        # Skip if message is outgoing
        if message.out:
            return
        
        try:
            # Check if post mentions creator
            if self.config["exclude_mentions"]:
                if message.text and "@Bedrock_RP" in message.text:
                    return
                
                # Check entities for mentions
                if message.entities:
                    for entity in message.entities:
                        if isinstance(entity, types.MessageEntityMention):
                            mention_text = message.text[entity.offset:entity.offset + entity.length]
                            if "Bedrock_RP" in mention_text:
                                return
            
            # Get target channel
            target = await message.client.get_entity(self._target_channel)
            
            # Prepare promo text
            promo_text = self.strings["promo_text"].format(
                self._target_channel,
                self._target_name
            )
            
            # Forward message with modifications
            if message.media:
                # If message has media
                caption = message.text or ""
                new_caption = caption + promo_text
                
                await message.client.send_file(
                    target,
                    message.media,
                    caption=new_caption,
                    parse_mode="html"
                )
            elif message.text:
                # Text-only message
                new_text = message.text + promo_text
                
                await message.client.send_message(
                    target,
                    new_text,
                    parse_mode="html"
                )
        
        except Exception as e:
            # Silent fail to avoid spam
            pass

    @loader.command()
    async def voretest(self, message):
        """<reply> - Test forwarding a specific message"""
        reply = await message.get_reply_message()
        
        if not reply:
            await utils.answer(message, "<b>❌ Reply to a message to test</b>")
            return
        
        if not self._target_channel:
            await utils.answer(message, "<b>❌ Target channel not set. Use .vores first</b>")
            return
        
        try:
            target = await message.client.get_entity(self._target_channel)
            
            promo_text = self.strings["promo_text"].format(
                self._target_channel,
                self._target_name
            )
            
            if reply.media:
                caption = reply.text or ""
                new_caption = caption + promo_text
                
                await message.client.send_file(
                    target,
                    reply.media,
                    caption=new_caption,
                    parse_mode="html"
                )
            elif reply.text:
                new_text = reply.text + promo_text
                
                await message.client.send_message(
                    target,
                    new_text,
                    parse_mode="html"
                )
            
            await utils.answer(message, "<b>✅ Test message forwarded</b>")
            
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))
```