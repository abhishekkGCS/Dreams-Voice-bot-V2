# # memory.py
# import os
# import json
# import motor.motor_asyncio
# from datetime import datetime

# # Try to import redis, but don't crash if it's missing
# try:
#     import redis.asyncio as redis
#     REDIS_AVAILABLE = True
# except ImportError:
#     REDIS_AVAILABLE = False


# class MemoryManager:
#     def __init__(self):
#         # 1. MongoDB (Long Term) - Always connect
#         mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
#         self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
#         self.db = self.mongo_client["jarvis_db"]
#         self.memory_collection = self.db["long_term_memory"]

#         # 2. Redis (Short Term) - Optional
#         self.redis_client = None
#         if REDIS_AVAILABLE:
#             try:
#                 self.redis_client = redis.Redis.from_url(
#                     os.getenv("REDIS_URL", "redis://localhost:6379/0")
#                 )
#                 print("✅ Redis connected")
#             except Exception:
#                 print("⚠️ Redis not available. Short-term memory disabled.")

#     # --- LONG TERM (MONGO) ---
#     async def save_fact(self, fact: str):
#         await self.memory_collection.insert_one({
#             "fact": fact,
#             "timestamp": datetime.now()
#         })

#     async def get_facts(self):
#         cursor = self.memory_collection.find({}, {"_id": 0, "fact": 1})
#         facts = await cursor.to_list(length=100)
#         return [f["fact"] for f in facts]

#     # --- SHORT TERM (REDIS) ---
#     # async def backup_session(self, session_id: str, livekit_messages: list):
#     #     if not self.redis_client:
#     #         return  # Silently skip if Redis isn't running
#     #     try:
#     #         serializable_history = [
#     #             {"role": msg.role, "text": msg.text_content}
#     #             for msg in livekit_messages
#     #             if msg.role in ["user", "assistant", "system"]
#     #         ]
#     #         await self.redis_client.setex(session_id, 3600, json.dumps(serializable_history))
#     #     except Exception as e:
#     #         print(f"⚠️ Redis backup failed: {e}")
#         # --- SHORT TERM (REDIS) ---
#     async def backup_session(self, session_id: str, livekit_messages: list):
#         if not self.redis_client:
#             return
#         try:
#             serializable_history = []
#             for msg in livekit_messages:
#                 # Safe-check: only backup real text messages, ignore handoffs/events
#                 if hasattr(msg, "role") and hasattr(msg, "text_content"):
#                     if msg.role in ["user", "assistant", "system"]:
#                         serializable_history.append({
#                             "role": msg.role,
#                             "text": msg.text_content or ""
#                         })
#             await self.redis_client.setex(session_id, 3600, json.dumps(serializable_history))
#         except Exception as e:
#             print(f"⚠️ Redis backup failed: {e}")

#     async def restore_session(self, session_id: str):
#         if not self.redis_client:
#             return None  # No Redis = no session to restore
#         try:
#             saved_history = await self.redis_client.get(session_id)
#             if saved_history:
#                 return json.loads(saved_history)
#         except Exception as e:
#             print(f"⚠️ Redis restore failed: {e}")
#         return None

# memory.py
import os
import json
import motor.motor_asyncio
from datetime import datetime

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class MemoryManager:
    def __init__(self):
        # 1. MongoDB (Long Term)
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
        self.db = self.mongo_client["jarvis_db"]
        self.memory_collection = self.db["long_term_memory"]

        # 2. Redis (Short Term)
        self.redis_client = None
        if REDIS_AVAILABLE:
            self.redis_client = redis.Redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379/0")
            )

    # --- LONG TERM (MONGO) ---
    async def save_fact(self, fact: str):
        await self.memory_collection.insert_one({
            "fact": fact,
            "timestamp": datetime.now()
        })

    async def get_facts(self):
        cursor = self.memory_collection.find({}, {"_id": 0, "fact": 1})
        facts = await cursor.to_list(length=100)
        return [f["fact"] for f in facts]

    # --- SHORT TERM (REDIS) ---
    async def backup_session(self, session_id: str, livekit_messages: list):
        if not self.redis_client:
            return
        try:
            serializable_history = []
            for msg in livekit_messages:
                if hasattr(msg, "role") and hasattr(msg, "text_content"):
                    if msg.role in ["user", "assistant", "system"]:
                        serializable_history.append({
                            "role": msg.role,
                            "text": msg.text_content or ""
                        })
            # Try to write to Redis
            await self.redis_client.setex(session_id, 3600, json.dumps(serializable_history))
        except Exception:
            # Catch ConnectionRefusedError silently so the agent doesn't crash
            pass

    async def restore_session(self, session_id: str):
        if not self.redis_client:
            return None
        try:
            # Try to read from Redis
            saved_history = await self.redis_client.get(session_id)
            if saved_history:
                return json.loads(saved_history)
        except Exception:
            pass
        return None