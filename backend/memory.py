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


class WorkingMemory:
    """
    In-session scratchpad tracking active context: current app, active project, and task.
    Enables pronoun resolution (e.g., 'close it', 'pause it', 'add task to it').
    """

    def __init__(self):
        self.current_app: str | None = None
        self.current_project: str | None = None
        self.current_task: str | None = None
        self.last_action: str | None = None

    def set_app(self, app_name: str):
        self.current_app = app_name
        self.last_action = f"opened/focused {app_name}"

    def clear_app(self, app_name: str | None = None):
        if app_name is None or (self.current_app and app_name.lower() in self.current_app.lower()):
            self.current_app = None
        self.last_action = f"closed {app_name or 'app'}"

    def set_project(self, project_name: str):
        self.current_project = project_name
        self.last_action = f"working on project {project_name}"

    def set_task(self, task_name: str):
        self.current_task = task_name

    def get_summary(self) -> str:
        """Returns a concise snapshot of what the assistant is currently tracking."""
        parts = []
        if self.current_app:
            parts.append(f"Active App: {self.current_app}")
        if self.current_project:
            parts.append(f"Active Project: {self.current_project}")
        if self.current_task:
            parts.append(f"Active Task: {self.current_task}")
        if not parts:
            return "No active app, project, or task currently in working memory."
        return "Working Memory Context: " + " | ".join(parts)

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
    
    
class WorkingMemory:
    """In-session scratchpad tracking active context (app, project, task)."""

    def __init__(self):
        self.current_app: str | None = None
        self.current_project: str | None = None
        self.current_task: str | None = None
        self.last_action: str | None = None

    def set_app(self, app_name: str):
        self.current_app = app_name
        self.last_action = f"opened/focused {app_name}"

    def clear_app(self, app_name: str | None = None):
        if app_name is None or (self.current_app and app_name.lower() in self.current_app.lower()):
            self.current_app = None
        self.last_action = f"closed {app_name or 'app'}"

    def set_project(self, project_name: str):
        self.current_project = project_name
        self.last_action = f"working on project {project_name}"

    def set_task(self, task_name: str):
        self.current_task = task_name

    def get_summary(self) -> str:
        parts = []
        if self.current_app:
            parts.append(f"Active App: {self.current_app}")
        if self.current_project:
            parts.append(f"Active Project: {self.current_project}")
        if self.current_task:
            parts.append(f"Active Task: {self.current_task}")
        if not parts:
            return "No active app, project, or task currently in working memory."
        return "Working Memory Context: " + " | ".join(parts)