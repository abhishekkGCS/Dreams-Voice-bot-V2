# backend/agent.py
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
    tts,
    log,
)
from livekit.agents.voice.agent_session import SessionConnectOptions
from livekit.plugins import deepgram, elevenlabs, silero, openai as lk_openai

# Custom modules
from tools import JarvisTools
from memory import MemoryManager, WorkingMemory
from router import IntentRouter
from fallbacks import EdgeTTS
from DREAMS_SYSTEM_PROMPT import DREAMS_SYSTEM_PROMPT
from metrics_collector import MetricsCollector
from metrics_server import start_metrics_server

load_dotenv()

LIVEKIT_LLM_TIMEOUT = float(os.getenv("LIVEKIT_LLM_TIMEOUT", "60.0"))
ENABLE_LIVEKIT_TOOLS = True

logger = log.logger


async def entrypoint(ctx: JobContext):
    session_id = f"chat_session:{ctx.room.name}"
    memory = MemoryManager()
    working_memory = WorkingMemory()
    metrics_collector = MetricsCollector()

    # --- RESTORE CONVERSATION HISTORY ---
    initial_ctx = llm.ChatContext()
    past_session = await memory.restore_session(session_id)
    if past_session:
        for msg in past_session:
            initial_ctx.add_message(role=msg["role"], content=msg["text"])
    else:
        initial_ctx.add_message(role="system", content=DREAMS_SYSTEM_PROMPT)

    # --- PRIMARY & BACKUP LOCAL OLLAMA MODELS ---
    primary_llm = lk_openai.LLM(
        model="llama3.2:3b",
        api_key="ollama",
        base_url="http://127.0.0.1:11434/v1",
        temperature=0.3,
    )
    backup_llm = lk_openai.LLM(
        model="llama3:latest",
        api_key="ollama",
        base_url="http://127.0.0.1:11434/v1",
        temperature=0.3,
    )

    # --- RESILIENT VOICE SESSION ---
    session = AgentSession(
        vad=silero.VAD.load(
            min_speech_duration=0.05,
            min_silence_duration=0.35,
            prefix_padding_duration=0.2,
        ),
        stt=deepgram.STT(
            model="nova-2",
            language="en",
            smart_format=True,
        ),
        llm=llm.FallbackAdapter(llm=[primary_llm, backup_llm]),
        tts=tts.FallbackAdapter(tts=[elevenlabs.TTS(), EdgeTTS()]),
        allow_interruptions=True,
        min_interruption_duration=0.2,
        min_endpointing_delay=0.1,
        conn_options=SessionConnectOptions(
            llm_conn_options=APIConnectOptions(timeout=LIVEKIT_LLM_TIMEOUT)
        ),
    )

    jarvis_tools = JarvisTools(working_memory=working_memory, metrics=metrics_collector)
    agent_tools = [jarvis_tools] if ENABLE_LIVEKIT_TOOLS else []

    agent = Agent(
        instructions="You are Dreams, a helpful and concise voice assistant.",
        chat_ctx=initial_ctx,
        tools=agent_tools,
    )

    # --- FAST PATH INTENT ROUTER ---
    @session.on("user_speech_committed")
    def on_user_speech(msg):
        user_text = msg.content if hasattr(msg, "content") else str(msg)
        intent, action = IntentRouter.classify(user_text)

        if intent == "DIRECT_TOOL":
            logger.info(f"⚡ FAST PATH triggered for action: {action}")
            metrics_collector.record_fast_path(action)

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

                await session.say(result)

            asyncio.create_task(run_fast_path())

    # --- METRICS COLLECTION & TRACING ---
    @session.on("metrics_collected")
    def on_metrics_collected(event):
        m = getattr(event, "metrics", event)
        metric_name = getattr(m, "type", None) or type(m).__name__

        if "STT" in metric_name:
            duration = getattr(m, "duration", 0)
            metrics_collector.record_stt(duration)
            logger.info(f"[TRACE] STT_FINAL | Duration: {duration:.2f}s")
        elif "LLM" in metric_name:
            ttft = getattr(m, "ttft", 0)
            metrics_collector.record_llm(ttft)
            logger.info(f"[TRACE] LLM_FIRST_TOKEN | TTFT: {ttft:.2f}s")
        elif "TTS" in metric_name:
            ttfb = getattr(m, "ttfb", 0)
            metrics_collector.record_tts(ttfb)
            logger.info(f"[TRACE] TTS_START -> AUDIO_FIRST_BYTE | TTFB: {ttfb:.2f}s")

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

    # --- CONVERSATION HOOKS ---
    @session.on("conversation_item_added")
    def on_conversation_item_added(event: ConversationItemAddedEvent):
        item = event.item
        if not hasattr(item, "role"):
            return

        if item.role == "user":
            logger.info("user spoke", extra={"text": item.text_content})
            metrics_collector.record_conversation("user", item.text_content)
            asyncio.create_task(memory.backup_session(session_id, session.history.items))
        elif item.role == "assistant":
            logger.info("dreams spoke", extra={"text": item.text_content})
            metrics_collector.record_conversation("assistant", item.text_content)
            asyncio.create_task(memory.backup_session(session_id, session.history.items))

    # --- GRACEFUL DISCONNECT ---
    @ctx.room.on("disconnected")
    def on_disconnected():
        logger.info("user disconnected, starting cleanup", extra={"session_id": session_id})
        asyncio.create_task(memory.save_fact(f"Conversation finished at session: {session_id}"))

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    print(f"Agent joined room: {ctx.room.name}")

    await session.start(room=ctx.room, agent=agent)

    # Start Ollama hardware monitoring
    asyncio.create_task(monitor_ollama(interval=2.0))

    # Start Metrics WebSocket Server on ws://localhost:8765
    asyncio.create_task(start_metrics_server(metrics_collector))

    # Greeting
    await session.generate_reply(
        instructions="Say: All systems online. Local model loaded. How can I help?",
        allow_interruptions=True,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))