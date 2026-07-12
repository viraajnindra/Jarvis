"""Voice pipeline: mic -> wakeword -> VAD -> STT -> agent -> streamed TTS.

Everything is local (mic and speakers are on the same machine as the backend), so
the pipeline captures and plays audio directly. State transitions broadcast over WS
so the voice-mode UI can reflect them. Barge-in: the wakeword firing during playback
stops speech and starts listening.

States: IDLE LISTENING TRANSCRIBING THINKING SPEAKING ERROR
"""

import asyncio
import logging
import queue
import re
import threading
import time
from collections.abc import AsyncIterator, Awaitable, Callable

import numpy as np

import config
from voice import tts

log = logging.getLogger("jarvis.voice")

SENTENCE_END = re.compile(r"(.+?[.!?])(\s|$)")


class VoicePipeline:
    def __init__(
        self,
        emit: Callable[[dict], Awaitable[None]],
        converse: Callable[[str, str], AsyncIterator[dict]],
        conv_id_getter: Callable[[], str],
    ):
        self._emit = emit
        self._converse = converse
        self._conv_id = conv_id_getter
        self._loop: asyncio.AbstractEventLoop | None = None
        self._frames: queue.Queue = queue.Queue()
        self._stream = None
        self._task: asyncio.Task | None = None
        self._running = False
        self._speaking = False
        self._interrupt = threading.Event()
        self._ptt = threading.Event()  # push-to-talk: skip wakeword
        self._oww = None
        self._vad = None
        self._stt = None
        self._any_tokens = False

    # ---- model loading (lazy, off the event loop) ----
    def _load_models(self) -> None:
        import openwakeword
        from openwakeword.model import Model
        from openwakeword.vad import VAD
        from faster_whisper import WhisperModel

        import os

        base = os.path.join(os.path.dirname(openwakeword.__file__), "resources", "models")
        self._oww = Model(
            wakeword_model_paths=[os.path.join(base, f"{config.WAKEWORD}.onnx")]
        )
        self._vad = VAD()
        self._stt = WhisperModel(config.STT_MODEL, device="cpu", compute_type="int8")
        log.info("voice models loaded")

    # ---- lifecycle ----
    async def start(self) -> None:
        if self._running:
            return
        self._loop = asyncio.get_running_loop()
        await asyncio.to_thread(self._load_models)
        self._running = True
        self._open_stream()
        self._task = asyncio.create_task(self._run())
        await self._set_state("LISTENING")

    async def stop(self) -> None:
        self._running = False
        self._interrupt.set()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self._task:
            self._task.cancel()
        await self._set_state("IDLE")

    def push_to_talk(self) -> None:
        """Force capture without the wakeword (called from a WS message / hotkey)."""
        self._ptt.set()

    # ---- audio capture ----
    def _open_stream(self) -> None:
        import sounddevice as sd

        def cb(indata, _frames, _t, status):  # runs on PortAudio thread
            if status:
                log.debug("audio status: %s", status)
            self._frames.put(indata[:, 0].copy())

        self._stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=config.FRAME_SAMPLES,
            callback=cb,
        )
        self._stream.start()

    async def _next_frame(self) -> np.ndarray:
        while True:
            try:
                return self._frames.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.01)

    # ---- main loop ----
    async def _run(self) -> None:
        try:
            while self._running:
                frame = await self._next_frame()
                if self._ptt.is_set():
                    self._ptt.clear()
                    await self._handle_utterance()
                    continue
                score = self._oww.predict(frame)[config.WAKEWORD]
                if score >= config.WAKEWORD_THRESHOLD:
                    log.info("wakeword (%.2f)", score)
                    self._drain()
                    await self._handle_utterance()
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001
            log.exception("voice loop crashed")
            await self._set_state("ERROR")

    def _drain(self) -> None:
        while not self._frames.empty():
            try:
                self._frames.get_nowait()
            except queue.Empty:
                break

    async def _handle_utterance(self) -> None:
        audio = await self._record_until_silence()
        if audio.size < config.SAMPLE_RATE // 2:  # < 0.5 s, likely noise
            await self._set_state("LISTENING")
            return
        await self._set_state("TRANSCRIBING")
        text = await asyncio.to_thread(self._transcribe, audio)
        text = text.strip()
        if not text:
            await self._set_state("LISTENING")
            return
        await self._emit({"type": "voice_transcript", "text": text})
        await self._respond(text)
        if self._running:
            await self._set_state("LISTENING")

    async def _record_until_silence(self) -> np.ndarray:
        chunks: list[np.ndarray] = []
        silence_ms = 0
        started = time.monotonic()
        self._vad.reset_states()
        while self._running:
            frame = await self._next_frame()
            chunks.append(frame)
            speech_prob = self._vad.predict(frame)
            frame_ms = 1000 * len(frame) / config.SAMPLE_RATE
            if speech_prob >= config.VAD_THRESHOLD:
                silence_ms = 0
            else:
                silence_ms += frame_ms
            if silence_ms >= config.VAD_SILENCE_MS and len(chunks) > 5:
                break
            if (time.monotonic() - started) * 1000 > config.MAX_UTTERANCE_MS:
                break
        return np.concatenate(chunks) if chunks else np.array([], dtype=np.int16)

    def _transcribe(self, audio: np.ndarray) -> str:
        pcm = audio.astype(np.float32) / 32768.0
        segments, _ = self._stt.transcribe(pcm, language="en", beam_size=1)
        return " ".join(s.text for s in segments)

    # ---- agent + TTS ----
    async def _respond(self, text: str) -> None:
        await self._set_state("THINKING")
        buf = ""
        final = ""
        self._any_tokens = False
        async for event in self._converse(self._conv_id(), text):
            if "assistant_token" in event:
                tok = event["assistant_token"]
                buf += tok
                await self._emit({"type": "assistant_token", "content": tok})
                buf = await self._flush_sentences(buf)
            elif "tool_call" in event:
                await self._emit({"type": "tool_call", **event["tool_call"]})
            elif event.get("done"):
                final = event["content"]
        # Memory-command replies arrive only as `final` (no tokens streamed);
        # normal replies leave a trailing partial sentence in buf.
        remainder = buf.strip() or (final.strip() if not self._any_tokens else "")
        if remainder:
            await self._speak(remainder)
        await self._emit({"type": "assistant_done", "content": final})

    async def _flush_sentences(self, buf: str) -> str:
        """Speak any complete sentences in buf; return the trailing partial."""
        self._any_tokens = True
        while True:
            m = SENTENCE_END.match(buf)
            if not m:
                return buf
            sentence = m.group(1).strip()
            buf = buf[m.end():]
            if sentence:
                await self._speak(sentence)

    async def _speak(self, text: str) -> None:
        await self._set_state("SPEAKING")
        pcm, rate = await asyncio.to_thread(tts.synth_pcm, text)
        self._interrupt.clear()
        await asyncio.to_thread(self._play_with_bargein, pcm, rate)

    def _play_with_bargein(self, pcm: np.ndarray, rate: int) -> None:
        import sounddevice as sd

        self._speaking = True
        block = rate // 10  # 100 ms
        try:
            with sd.OutputStream(samplerate=rate, channels=1, dtype="int16") as out:
                for i in range(0, len(pcm), block):
                    if self._interrupt.is_set() or not self._running:
                        break
                    # barge-in: scan live frames for the wakeword while speaking
                    if self._wakeword_in_queue():
                        log.info("barge-in")
                        self._interrupt.set()
                        break
                    out.write(pcm[i : i + block])
        finally:
            self._speaking = False

    def _wakeword_in_queue(self) -> bool:
        fired = False
        while not self._frames.empty():
            try:
                frame = self._frames.get_nowait()
            except queue.Empty:
                break
            if self._oww.predict(frame)[config.WAKEWORD] >= config.WAKEWORD_THRESHOLD:
                fired = True
        return fired

    async def _set_state(self, state: str) -> None:
        await self._emit({"type": "voice_state", "state": state})
