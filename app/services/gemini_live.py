"""Gemini Live API Service.

Manages real-time bidirectional streaming audio, speech transcriptions,
and live tool execution with Google Gemini Live API.
"""

import asyncio
import base64
import json
import logging
from datetime import datetime, date
from typing import Optional, Callable, Dict, Any, List
from google import genai
from google.genai import types

from app.database import get_db
import app.config as config
from app.tools.receptionist_tools import TOOL_REGISTRY, RECEPTIONIST_TOOL_FUNCTIONS

logger = logging.getLogger("gemini_live")


def get_receptionist_prompt() -> str:
    """Generate the system prompt for the AI Receptionist."""
    today_str = date.today().isoformat()
    return f"""You are {config.RECEPTIONIST_NAME}, the elite Corporate AI Receptionist for {config.COMPANY_NAME}.
Today's date is {today_str}.

COMPANY CONTEXT:
- Company: {config.COMPANY_NAME}
- Industry: {config.COMPANY_INDUSTRY}
- Address: {config.COMPANY_LOCATION}
- Operating Hours: {config.COMPANY_HOURS}

CORE PERSONA & VOICE STYLE:
- Warm, poised, articulate, and confident front-desk professional.
- Speak naturally and conversationally. Keep spoken responses concise (1-3 sentences) so the conversation flows naturally like an in-person or phone exchange.
- Avoid reading out long lists or bullet points verbatim over voice. Offer to help or summarize.

RECEPTIONIST RESPONSIBILITIES & TOOL USAGE:
1. GREETING:
   - Greet callers and visitors warmly with: "Good day! Welcome to {config.COMPANY_NAME}. My name is {config.RECEPTIONIST_NAME}. How may I direct your call or assist you today?"
2. VISITOR & CALLER INQUIRIES:
   - For office address, visitor parking, directions, guest Wi-Fi, or security badge check-in, call `get_company_info(topic=...)`.
3. DIRECTORY & STAFF SEARCH:
   - When a caller asks for a specific person or department (e.g. Sales, HR, Engineering, CEO, Billing), use `lookup_directory(query=...)`.
   - Report their title, extension, and whether they are currently Available, In a Meeting, or Out of the Office.
4. CALL ROUTING & TRANSFERS:
   - If the caller wants to be connected to an available staff member or department, call `transfer_call(recipient_or_department=...)`.
5. APPOINTMENTS & SCHEDULING:
   - To book a visit or meeting, first check available time slots using `check_availability(staff_or_department=..., date_str=...)`.
   - Ask for their name, contact phone/email, and preferred time slot.
   - Once agreed upon, confirm and finalize with `book_appointment(...)`.
   - If a caller asks to cancel an existing booking, call `cancel_appointment(...)`.
6. TAKING MESSAGES:
   - If the requested team member is in a meeting, away from their desk, or out of office, politely explain this and offer: "Would you like me to take a message for them or connect you with their team?"
   - When taking a message, gather their name, callback contact (phone/email), and the message details, then execute `leave_message(caller_name=..., contact_info=..., recipient_name=..., message=..., urgency=...)`.

CRITICAL INSTRUCTION:
Always invoke the appropriate tool whenever a caller makes a factual inquiry, requests directory search, asks for an appointment, or leaves a message.
Never fabricate office information or assume appointment availability without checking first.
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
        if not self.api_key:
            await self.client_send(
                {
                    "type": "error",
                    "message": "Gemini API Key is missing. Please provide your API key in Settings or .env.",
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
        tool_args = fc.args or {}

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
                result = await TOOL_REGISTRY[tool_name](**tool_args)
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

            # Works with async context manager pattern for db connections
            async with get_db() as db:
                await db.execute(
                    """INSERT INTO call_logs
                       (session_id, caller_identifier, started_at, ended_at, duration_seconds, summary, full_transcript, actions_taken)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        f"call-{int(self.started_at.timestamp())}",
                        "Front Desk Voice Caller",
                        self.started_at.isoformat(),
                        ended_at.isoformat(),
                        duration,
                        summary,
                        transcript_str,
                        actions_str,
                    ),
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to save call log: {e}")