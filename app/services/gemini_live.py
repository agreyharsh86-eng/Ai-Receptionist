"""Gemini Live API Service.

Manages real-time bidirectional streaming audio, speech transcriptions,
and live tool execution with Google Gemini Live API.
"""

import asyncio
import base64
import json
import logging
import inspect
from datetime import datetime, date
from typing import Optional, Callable, Dict, Any, List
from google import genai
from google.genai import types

from app.database_mongo import save_call_log
import app.config as config
from app.tools.receptionist_tools import TOOL_REGISTRY, RECEPTIONIST_TOOL_FUNCTIONS

logger = logging.getLogger("gemini_live")


def get_receptionist_prompt() -> str:
    """Generate the system prompt for the AI Receptionist."""
    today_str = date.today().isoformat()
    return f"""You are {config.RECEPTIONIST_NAME}, the AI voice receptionist for {config.COMPANY_NAME}.
Today is {today_str}.

PERSONALITY:
- Warm, natural, professional. Sound like a real human receptionist, not a chatbot.
- Keep every response to 1-2 short sentences. Never read out long lists.
- Ask only ONE question per turn. Never ask multiple things at once.
- Use conversational language: "Sure!", "Of course.", "Got it.", "Let me check that for you."
- Never say "I apologize" or "I'm sorry" repeatedly. Keep it natural.

APPOINTMENT BOOKING — STEP BY STEP:
When a patient mentions wanting an appointment, a doctor, or a symptom:

STEP 1 — Find doctor: Call search_doctors(query="symptom or specialty").
STEP 2 — Check availability: Call check_availability(staff_or_department=doctor_name, date_str=date).
STEP 3 — Present ONE doctor and 2-3 slots. E.g.: "Dr. Sharma is free tomorrow at 10 AM, 11 AM, or 2 PM. Which works?"
STEP 4 — Collect missing info ONE AT A TIME:
  - If no slot: "Which time works best for you?"
  - If no name: "Could I have your full name?"
  - If no contact: "And your phone number?"
STEP 5 — Confirm: "So that's [Doctor] on [date] at [time] for [Name] — shall I confirm?"
STEP 6 — Book: Call book_appointment(...) ONLY after patient says yes/confirm.
STEP 7 — Report result: "Done! Booking #[ID] confirmed. Please arrive 10 minutes early."

RULES:
- NEVER invent doctors, slots, or availability. Always use the tools.
- NEVER confirm a booking unless book_appointment returns status=confirmed.
- If a slot is taken, immediately offer the next available slot.
- If the patient corrects something ("no, change the time"), update and re-confirm.
- Do not repeat information already given. Do not re-ask for info already provided.

OTHER TASKS:
- Directory: lookup_directory(query=...)
- Company info: get_company_info(topic=...)
- Call transfer: transfer_call(recipient_or_department=...)
- Cancel appointment: cancel_appointment(visitor_name=..., date_str=...)
- Leave message: leave_message(caller_name=..., contact_info=..., recipient_name=..., message=...)
"""


class LiveSessionManager:
    """Handles an active WebSocket bridge between client browser and Gemini Live API."""

    def __init__(
        self,
        client_send_cb: Callable[[Dict[str, Any]], Any],
        api_key: Optional[str] = None,
        voice_name: Optional[str] = None,
    ):
        self.client_send = client_send_cb
        self.api_key = (
            api_key or getattr(config, "GEMINI_API_KEY", "")
        ).strip()
        self.voice_name = voice_name or getattr(
            config, "DEFAULT_VOICE", "Aoede"
        )
        self.is_running = False
        self.session = None
        self.started_at = datetime.now()
        self.transcript: List[Dict[str, str]] = []
        self.actions_taken: List[Dict[str, Any]] = []

    async def run_session(self, inbound_queue: asyncio.Queue):
        """Run the live session loop."""
        if not config.is_valid_gemini_key(self.api_key):
            await self.client_send(
                {
                    "type": "error",
                    "message": "Gemini API Key is missing or invalid. Please provide your API key in Settings or .env.",
                }
            )
            return

        client = genai.Client(api_key=self.api_key)
        prompt = get_receptionist_prompt()

        live_config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice_name
                    )
                )
            ),
            system_instruction=types.Content(
         parts=[types.Part.from_text(text=prompt)]
        ),
            tools=RECEPTIONIST_TOOL_FUNCTIONS,
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )

        self.is_running = True

        try:
            async with client.aio.live.connect(
                model=config.GEMINI_LIVE_MODEL, config=live_config
            ) as session:
                self.session = session
                await self.client_send(
                    {
                        "type": "status",
                        "status": "connected",
                        "message": f"Connected to {config.RECEPTIONIST_NAME} ({self.voice_name} voice)",
                    }
                )

                # Kickoff initial greeting prompt to Gemini Live
                await session.send_realtime_input(
                    text="The caller has just connected to the front desk. Greet them warmly and professionally as the receptionist."
                )

                # Run sender and receiver concurrently
                receiver_task = asyncio.create_task(
                    self._receive_from_gemini(session)
                )
                sender_task = asyncio.create_task(
                    self._send_to_gemini(session, inbound_queue)
                )

                done, pending = await asyncio.wait(
                    [receiver_task, sender_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()

                await asyncio.gather(*pending, return_exceptions=True)

        except Exception as e:
            logger.error(f"Live session exception: {e}", exc_info=True)
            await self.client_send(
                {"type": "error", "message": f"Live connection error: {str(e)}"}
            )
        finally:
            self.is_running = False
            self.session = None
            await self._save_call_log()
            await self.client_send(
                {
                    "type": "status",
                    "status": "disconnected",
                    "message": "Call ended",
                }
            )

    async def _send_to_gemini(self, session, inbound_queue: asyncio.Queue):
        """Consume messages from the browser queue and forward to Gemini Live."""
        try:
            while self.is_running:
                item = await inbound_queue.get()
                try:
                    if item is None:  # Shutdown signal
                        break

                    msg_type = item.get("type")

                    if msg_type == "audio":
                        # Raw PCM 16kHz audio from browser
                        raw_b64 = item.get("data", "")
                        if raw_b64:
                            pcm_bytes = base64.b64decode(raw_b64)
                            await session.send_realtime_input(
                                audio=types.Blob(
                                    data=pcm_bytes,
                                    mime_type="audio/pcm;rate=16000",
                                )
                            )

                    elif msg_type == "text":
                        text_content = item.get("text", "").strip()
                        if text_content:
                            self.transcript.append(
                                {"role": "user", "text": text_content}
                            )
                            await session.send_realtime_input(text=text_content)

                    elif msg_type == "audio_stream_end":
                        await session.send_realtime_input(audio_stream_end=True)

                    elif msg_type == "end_call":
                        self.is_running = False
                        break

                finally:
                    inbound_queue.task_done()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error sending to Gemini: {e}")

    async def _execute_single_tool(
        self, fc: types.FunctionCall
    ) -> types.FunctionResponse:
        """Helper to execute an individual tool call asynchronously."""
        tool_name = fc.name
        raw_args = fc.args or {}

        # Safely convert protobuf map or dict-like object to a standard Python dict
        if hasattr(raw_args, "items"):
            tool_args = {str(k): v for k, v in raw_args.items()}
        elif isinstance(raw_args, dict):
            tool_args = dict(raw_args)
        else:
            tool_args = {}

        logger.info(
            f"Executing tool: {tool_name} with args: {tool_args}"
        )

        # Notify client UI of active tool execution
        await self.client_send(
            {
                "type": "tool_executing",
                "name": tool_name,
                "args": tool_args,
            }
        )

        self.actions_taken.append({"tool": tool_name, "args": tool_args})

        result = {"error": f"Tool '{tool_name}' not recognized"}

        if tool_name in TOOL_REGISTRY:
            try:
                tool_fn = TOOL_REGISTRY[tool_name]
                if inspect.iscoroutinefunction(tool_fn):
                    result = await tool_fn(**tool_args)
                elif callable(tool_fn):
                    res = tool_fn(**tool_args)
                    if inspect.iscoroutine(res):
                        result = await res
                    else:
                        result = res
            except Exception as ex:
                logger.error(
                    f"Tool execution failed for {tool_name}: {ex}",
                    exc_info=True,
                )
                result = {"error": str(ex)}

        # Notify client UI of tool result
        await self.client_send(
            {
                "type": "tool_result",
                "name": tool_name,
                "result": result,
            }
        )

        return types.FunctionResponse(
            name=tool_name,
            id=fc.id,
            response={"result": result},
        )

    async def _receive_from_gemini(self, session):
        """Receive responses, audio, transcripts, and tool calls from Gemini Live."""
        try:
            async for response in session.receive():
                if not self.is_running:
                    break

                # 1. Server Content (Audio & Transcripts)
                content = response.server_content
                if content:
                    # Model Turn (Audio parts)
                    if content.model_turn:
                        for part in content.model_turn.parts:
                            if (
                                part.inline_data
                                and part.inline_data.data
                            ):
                                # Raw PCM 24kHz audio bytes from Gemini
                                audio_b64 = base64.b64encode(
                                    part.inline_data.data
                                ).decode("utf-8")
                                await self.client_send(
                                    {
                                        "type": "audio",
                                        "data": audio_b64,
                                        "rate": 24000,
                                    }
                                )

                    # Input transcription (caller speech)
                    if (
                        content.input_transcription
                        and content.input_transcription.text
                    ):
                        user_text = (
                            content.input_transcription.text.strip()
                        )
                        if user_text:
                            self.transcript.append(
                                {"role": "user", "text": user_text}
                            )
                            await self.client_send(
                                {
                                    "type": "transcript",
                                    "role": "user",
                                    "text": user_text,
                                }
                            )

                    # Output transcription (receptionist speech)
                    if (
                        content.output_transcription
                        and content.output_transcription.text
                    ):
                        ai_text = (
                            content.output_transcription.text.strip()
                        )
                        if ai_text:
                            self.transcript.append(
                                {"role": "model", "text": ai_text}
                            )
                            await self.client_send(
                                {
                                    "type": "transcript",
                                    "role": "model",
                                    "text": ai_text,
                                }
                            )

                    # Interruption signal (caller began speaking while model was outputting)
                    if content.interrupted:
                        await self.client_send({"type": "interrupted"})

                # 2. Tool Calls
                if response.tool_call:
                    # Parallel tool execution using asyncio.gather
                    function_responses = await asyncio.gather(
                        *[
                            self._execute_single_tool(fc)
                            for fc in response.tool_call.function_calls
                        ]
                    )

                    # Send all tool execution results back to Gemini Live
                    if function_responses:
                        await session.send_tool_response(
                            function_responses=function_responses
                        )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(
                f"Error receiving from Gemini: {e}", exc_info=True
            )
            await self.client_send(
                {
                    "type": "error",
                    "message": f"Live stream error: {str(e)}",
                }
            )

    async def _save_call_log(self):
        """Save call summary and transcript to SQLite cleanly."""
        try:
            ended_at = datetime.now()
            duration = int(
                (ended_at - self.started_at).total_seconds()
            )

            if not self.transcript and not self.actions_taken:
                return  # Skip empty or instant disconnects

            transcript_str = json.dumps(
                self.transcript, ensure_ascii=False
            )
            actions_str = json.dumps(
                self.actions_taken, ensure_ascii=False
            )

            summary = f"Call duration: {duration}s. {len(self.transcript)} dialogue turns. Actions: {len(self.actions_taken)}."

            await save_call_log(
                session_id=f"call-{int(self.started_at.timestamp())}",
                caller_identifier="Front Desk Voice Caller",
                started_at=self.started_at,
                ended_at=ended_at,
                duration_seconds=duration,
                summary=summary,
                full_transcript=transcript_str,
                actions_taken=actions_str,
            )
        except Exception as e:
            logger.error(f"Failed to save call log: {e}")