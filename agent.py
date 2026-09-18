# # agent.py
# import os
# import asyncio
# from dotenv import load_dotenv
# from monitor import monitor_ollama  # <-- THIS IS THE IMPORT YOU WERE MISSING!

# from livekit.agents import (
#     Agent,
#     AgentSession,
#     AutoSubscribe,
#     ConversationItemAddedEvent,
#     JobContext,
#     WorkerOptions,
#     APIConnectOptions,
#     cli,
#     llm,
#     log,
# )
# from livekit.agents.voice.agent_session import SessionConnectOptions
# from livekit.plugins import deepgram, elevenlabs, silero, openai as lk_openai

# # Our custom modules
# from tools import JarvisTools
# from memory import MemoryManager


# from router import IntentRouter
# from tools import JarvisTools

# from DREAMS_SYSTEM_PROMPT import DREAMS_SYSTEM_PROMPT

# load_dotenv()

# # Increase the LiveKit LLM API timeout for local Ollama requests.
# # The default timeout is too short for some local model completion responses.
# LIVEKIT_LLM_TIMEOUT = float(os.getenv("LIVEKIT_LLM_TIMEOUT", "60.0"))
# ENABLE_LIVEKIT_TOOLS = True
# #ENABLE_LIVEKIT_TOOLS = os.getenv("ENABLE_LIVEKIT_TOOLS", "false").strip().lower() in ("1", "true", "yes")

# logger = log.logger



# async def entrypoint(ctx: JobContext):
#     session_id = f"chat_session:{ctx.room.name}"
#     memory = MemoryManager()

#     # --- RESTORE MEMORY ---
#     initial_ctx = llm.ChatContext()
#     past_session = await memory.restore_session(session_id)
#     if past_session:
#         print("🔄 RECOVERING SESSION FROM REDIS!")
#         for msg in past_session:
#             initial_ctx.add_message(role=msg["role"], content=msg["text"])
#     else:
#         initial_ctx.add_message(
#             role="system",
#             content=DREAMS_SYSTEM_PROMPT,
#         )

#     # --- BUILD SESSION WITH LOCAL OLLAMA GEMMA ---
#     session = AgentSession(
#         vad=silero.VAD.load(),
#         stt=deepgram.STT(),
#         llm=lk_openai.LLM(
#             model="llama3.2:3b",
#             api_key="ollama",
#             base_url="http://127.0.0.1:11434/v1",
#             temperature=0.3,
#         ),
#         tts=elevenlabs.TTS(),
#         conn_options=SessionConnectOptions(
#             llm_conn_options=APIConnectOptions(timeout=LIVEKIT_LLM_TIMEOUT)
#         ),
#     )

#     agent_tools = [JarvisTools()] if ENABLE_LIVEKIT_TOOLS else []
#     if not ENABLE_LIVEKIT_TOOLS:
#         logger.warning(
#             "LiveKit tools are disabled for the selected local Ollama model. "
#             "Set ENABLE_LIVEKIT_TOOLS=true only if your model/provider supports function calling."
#         )

#     agent = Agent(
#         instructions="You are Dreams, a helpful and concise voice assistant.",
#         chat_ctx=initial_ctx,
#         tools=agent_tools,
#     )
    
#     # --- FULL EXECUTION TRACE ---
#     @session.on("metrics_collected")
#     def on_metrics_collected(event):
#         metrics = getattr(event, "metrics", event)
#         metric_name = getattr(metrics, "type", None) or type(metrics).__name__
#         if "STT" in metric_name:
#             logger.info(f"[TRACE] STT_FINAL | Duration: {getattr(metrics, 'duration', 0):.2f}s")
#         elif "LLM" in metric_name:
#             ttft = getattr(metrics, "ttft", 0)
#             logger.info(f"[TRACE] LLM_FIRST_TOKEN | Time To First Token: {ttft:.2f}s")
#         elif "TTS" in metric_name:
#             ttfb = getattr(metrics, 'ttfb', 0)
#             logger.info(f"[TRACE] TTS_START -> AUDIO_FIRST_BYTE | Time To First Byte: {ttfb:.2f}s")

#     @session.on("user_started_speaking")
#     def on_user_speaking():
#         logger.info("[TRACE] 🎤 USER_SPEECH (Started)")
        
#     @session.on("user_stopped_speaking")
#     def on_user_stopped():
#         logger.info("[TRACE] 🛑 USER_SPEECH (Stopped) -> LLM_START")
        
#     @session.on("agent_started_speaking")
#     def on_agent_speaking():
#         logger.info("[TRACE] 🔊 AUDIO_PLAYING (Agent speaking)")
        
#     @session.on("agent_stopped_speaking")
#     def on_agent_stopped():
#         logger.info("[TRACE] ✅ COMPLETE")

#     # --- CONVERSATION HOOKS (STRUCTURED LOGS) ---
#     @session.on("conversation_item_added")
#     def on_conversation_item_added(event: ConversationItemAddedEvent):
#         item = event.item
#         # Safety check: some internal LiveKit messages (like AgentHandoff) don't have a 'role'
#         if not hasattr(item, "role"):
#             return
            
#         if item.role == "user":
#             logger.info("user spoke", extra={"text": item.text_content})
#             asyncio.create_task(memory.backup_session(session_id, session.history.items))
#         elif item.role == "assistant":
#             logger.info("dreams spoke", extra={"text": item.text_content})
#             asyncio.create_task(memory.backup_session(session_id, session.history.items))

#     # --- GRACEFUL DISCONNECT ---
#     @ctx.room.on("disconnected")
#     def on_disconnected():
#         logger.info("user disconnected, starting graceful cleanup", extra={"session_id": session_id})
#         asyncio.create_task(
#             memory.save_fact(f"Conversation finished at session: {session_id}")
#         )
#         logger.info("cleanup complete, shutting down worker")

#     await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
#     print(f"Agent joined room: {ctx.room.name}")

#     await session.start(room=ctx.room, agent=agent)
    
#     # Start tracking Ollama's CPU/RAM usage in the background
#     asyncio.create_task(monitor_ollama(interval=2.0))

#     # --- GREETING ---
#     await session.generate_reply(
#         instructions="Say: All systems online. Local model loaded. How can I help?",
#         allow_interruptions=True,
#     )


#     # Instantiate tools and router
#     jarvis_tools = JarvisTools()

#     @session.on("user_speech_committed")
#     def on_user_speech(msg):
#         # Grab the text the user just spoke
#         user_text = msg.content if hasattr(msg, "content") else str(msg)
        
#         intent, action = IntentRouter.classify(user_text)
        
#         # FAST PATH EXECUTION
#         if intent == "DIRECT_TOOL":
#             logger.info(f"⚡ FAST PATH triggered for action: {action}")
            
#             async def run_fast_path():
#                 if action == "time":
#                     result = await jarvis_tools.get_time()
#                 elif action == "media_pause":
#                     result = await jarvis_tools.media_control("pause")
#                 elif action == "media_play":
#                     result = await jarvis_tools.media_control("play")
#                 elif action == "media_next":
#                     result = await jarvis_tools.media_control("next")
#                 elif action == "system_status":
#                     result = await jarvis_tools.get_system_info()
#                 else:
#                     return
                
#                 # Speak result directly to the user bypassing the LLM
#                 await session.say(result)

#             asyncio.create_task(run_fast_path())



# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
    


# agent.py
import os
import asyncio
from dotenv import load_dotenv
from monitor import monitor_ollama

from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    ConversationItemAddedEvent,
    JobContext,
    WorkerOptions,
    APIConnectOptions,
    cli,
    llm,
    log,
)
from livekit.agents.voice.agent_session import SessionConnectOptions
from livekit.plugins import deepgram, elevenlabs, silero, openai as lk_openai

# Our custom modules
from tools import JarvisTools
from memory import MemoryManager
from router import IntentRouter
from DREAMS_SYSTEM_PROMPT import DREAMS_SYSTEM_PROMPT

load_dotenv()

# Increase the LiveKit LLM API timeout for local Ollama requests.
LIVEKIT_LLM_TIMEOUT = float(os.getenv("LIVEKIT_LLM_TIMEOUT", "60.0"))
ENABLE_LIVEKIT_TOOLS = True

logger = log.logger


async def entrypoint(ctx: JobContext):
    session_id = f"chat_session:{ctx.room.name}"
    memory = MemoryManager()

    # --- RESTORE MEMORY ---
    initial_ctx = llm.ChatContext()
    past_session = await memory.restore_session(session_id)
    if past_session:
        print("🔄 RECOVERING SESSION FROM REDIS!")
        for msg in past_session:
            initial_ctx.add_message(role=msg["role"], content=msg["text"])
    else:
        initial_ctx.add_message(
            role="system",
            content=DREAMS_SYSTEM_PROMPT,
        )

    # --- BUILD SESSION WITH LOCAL OLLAMA ---
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        llm=lk_openai.LLM(
            model="llama3.2:3b",
            api_key="ollama",
            base_url="http://127.0.0.1:11434/v1",
            temperature=0.3,
        ),
        tts=elevenlabs.TTS(),
        conn_options=SessionConnectOptions(
            llm_conn_options=APIConnectOptions(timeout=LIVEKIT_LLM_TIMEOUT)
        ),
    )

    jarvis_tools = JarvisTools()
    agent_tools = [jarvis_tools] if ENABLE_LIVEKIT_TOOLS else []

    agent = Agent(
        instructions="You are Dreams, a helpful and concise voice assistant.",
        chat_ctx=initial_ctx,
        tools=agent_tools,
    )

    # --- FAST PATH INTENT ROUTER ---
    # Intercepts deterministic speech commands and executes tools instantly without waiting for Ollama
    @session.on("user_speech_committed")
    def on_user_speech(msg):
        user_text = msg.content if hasattr(msg, "content") else str(msg)
        intent, action = IntentRouter.classify(user_text)

        if intent == "DIRECT_TOOL":
            logger.info(f"⚡ FAST PATH triggered for action: {action}")

            async def run_fast_path():
                if action == "time":
                    result = await jarvis_tools.get_time()
                elif action == "media_pause":
                    result = await jarvis_tools.media_control("pause")
                elif action == "media_play":
                    result = await jarvis_tools.media_control("play")
                elif action == "media_next":
                    result = await jarvis_tools.media_control("next")
                elif action == "system_status":
                    result = await jarvis_tools.get_system_info()
                else:
                    return

                # Send directly to ElevenLabs TTS
                await session.say(result)

            asyncio.create_task(run_fast_path())

    # --- FULL EXECUTION TRACE ---
    @session.on("metrics_collected")
    def on_metrics_collected(event):
        metrics = getattr(event, "metrics", event)
        metric_name = getattr(metrics, "type", None) or type(metrics).__name__
        if "STT" in metric_name:
            logger.info(f"[TRACE] STT_FINAL | Duration: {getattr(metrics, 'duration', 0):.2f}s")
        elif "LLM" in metric_name:
            ttft = getattr(metrics, "ttft", 0)
            logger.info(f"[TRACE] LLM_FIRST_TOKEN | Time To First Token: {ttft:.2f}s")
        elif "TTS" in metric_name:
            ttfb = getattr(metrics, 'ttfb', 0)
            logger.info(f"[TRACE] TTS_START -> AUDIO_FIRST_BYTE | Time To First Byte: {ttfb:.2f}s")

    @session.on("user_started_speaking")
    def on_user_speaking():
        logger.info("[TRACE] 🎤 USER_SPEECH (Started)")

    @session.on("user_stopped_speaking")
    def on_user_stopped():
        logger.info("[TRACE] 🛑 USER_SPEECH (Stopped) -> LLM_START")

    @session.on("agent_started_speaking")
    def on_agent_speaking():
        logger.info("[TRACE] 🔊 AUDIO_PLAYING (Agent speaking)")

    @session.on("agent_stopped_speaking")
    def on_agent_stopped():
        logger.info("[TRACE] ✅ COMPLETE")

    # --- CONVERSATION HOOKS (STRUCTURED LOGS) ---
    @session.on("conversation_item_added")
    def on_conversation_item_added(event: ConversationItemAddedEvent):
        item = event.item
        if not hasattr(item, "role"):
            return

        if item.role == "user":
            logger.info("user spoke", extra={"text": item.text_content})
            asyncio.create_task(memory.backup_session(session_id, session.history.items))
        elif item.role == "assistant":
            logger.info("dreams spoke", extra={"text": item.text_content})
            asyncio.create_task(memory.backup_session(session_id, session.history.items))

    # --- GRACEFUL DISCONNECT ---
    @ctx.room.on("disconnected")
    def on_disconnected():
        logger.info("user disconnected, starting graceful cleanup", extra={"session_id": session_id})
        asyncio.create_task(
            memory.save_fact(f"Conversation finished at session: {session_id}")
        )
        logger.info("cleanup complete, shutting down worker")

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    print(f"Agent joined room: {ctx.room.name}")

    await session.start(room=ctx.room, agent=agent)

    # Start tracking Ollama's CPU/RAM usage in the background
    asyncio.create_task(monitor_ollama(interval=2.0))

    # --- GREETING ---
    await session.generate_reply(
        instructions="Say: All systems online. Local model loaded. How can I help?",
        allow_interruptions=True,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))