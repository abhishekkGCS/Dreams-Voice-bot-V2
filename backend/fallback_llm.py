# backend/fallbacks.py
import edge_tts
from livekit.agents import tts, utils, APIConnectOptions

class EdgeTTS(tts.TTS):
    """Zero-token, unlimited neural Text-to-Speech provider for LiveKit."""

    def __init__(self, voice: str = "en-US-ChristopherNeural"):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=24000,
            num_channels=1,
        )
        self._voice = voice

    def synthesize(self, text: str, *, conn_options: APIConnectOptions = APIConnectOptions()) -> "EdgeChunkedStream":
        return EdgeChunkedStream(tts=self, input_text=text, conn_options=conn_options)


class EdgeChunkedStream(tts.ChunkedStream):
    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        communicate = edge_tts.Communicate(self._input_text, self._tts._voice)
        audio_data = bytearray()

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])

        output_emitter.initialize(
            request_id=utils.shortuuid(),
            sample_rate=24000,
            num_channels=1,
            mime_type="audio/mpeg"
        )
        output_emitter.push(bytes(audio_data))