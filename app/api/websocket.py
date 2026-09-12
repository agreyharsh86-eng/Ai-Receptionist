"""FastAPI WebSocket Endpoint for Real-Time Receptionist Streaming."""

import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

from app.services.gemini_live import LiveSessionManager
import app.config as config

logger = logging.getLogger("websocket_api")
router = APIRouter()

@router.websocket("/ws/live")
async def websocket_live_endpoint(
    websocket: WebSocket,
    api_key: Optional[str] = Query(None),
    voice: Optional[str] = Query(None)
):
    await websocket.accept()
    logger.info("Client WebSocket connected to /ws/live")

    # Queue for routing inbound messages from browser to Gemini Live
    inbound_queue = asyncio.Queue()

    async def client_send_callback(message_dict):
        try:
            await websocket.send_text(json.dumps(message_dict))
        except Exception as e:
            logger.debug(f"Error sending to WebSocket client: {e}")

    # Determine API key
    effective_api_key = api_key or config.GEMINI_API_KEY
    effective_voice = voice or config.DEFAULT_VOICE

    session_manager = LiveSessionManager(
        client_send_cb=client_send_callback,
        api_key=effective_api_key,
        voice_name=effective_voice
    )

    # Launch Gemini Live session in background
    live_task = asyncio.create_task(session_manager.run_session(inbound_queue))

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
                msg_type = data.get("type")

                if msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    continue

                if msg_type == "hangup" or msg_type == "end_call":
                    await inbound_queue.put({"type": "end_call"})
                    break

                # Put message into queue for Live session
                await inbound_queue.put(data)

            except json.JSONDecodeError:
                logger.warning(f"Malformed JSON from client: {raw_text[:100]}")
    except WebSocketDisconnect:
        logger.info("Client disconnected WebSocket.")
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        # Signal session to terminate
        await inbound_queue.put(None)
        if not live_task.done():
            live_task.cancel()
            try:
                await live_task
            except asyncio.CancelledError:
                pass
        logger.info("WebSocket connection cleanup complete.")
