#!/usr/bin/env python3
"""
OpenClaw Gateway WebSocket Client Example

This example demonstrates how to connect, authenticate, and communicate with the 
OpenClaw Gateway WebSocket server asynchronously using Python. It handles the initial 
handshake, listens to real-time events (agent thought streams, tool invocations),
and sends chat queries.

Requirements:
    pip install websockets aiohttp

Usage:
    python client.py --host localhost --port 18789 --token YOUR_GATEWAY_TOKEN
"""

import asyncio
import sys
import json
import uuid
import argparse
import websockets

async def receive_messages(websocket):
    """Listens for incoming WebSocket frames and prints events/responses."""
    try:
        async for message in websocket:
            try:
                frame = json.loads(message)
                frame_type = frame.get("type")

                if frame_type == "res":
                    # Handle method responses
                    id_ = frame.get("id")
                    ok = frame.get("ok")
                    payload = frame.get("payload")
                    error = frame.get("error")
                    
                    if ok:
                        print(f"\n[Response {id_}] Success: {json.dumps(payload, indent=2)}")
                    else:
                        print(f"\n[Response {id_}] Error: {json.dumps(error, indent=2)}")

                elif frame_type == "event":
                    # Handle real-time push events from the gateway
                    event_name = frame.get("event")
                    payload = frame.get("payload") or {}
                    
                    if event_name == "chat.event" or "chat" in event_name:
                        state = payload.get("state")
                        if state == "delta":
                            # Streaming token
                            print(payload.get("deltaText", ""), end="", flush=True)
                        elif state == "final":
                            print(f"\n\n[Agent Finished] Stop Reason: {payload.get('stopReason')}")
                        elif state == "aborted":
                            print(f"\n\n[Agent Aborted] Stop Reason: {payload.get('stopReason')}")
                        elif state == "error":
                            print(f"\n\n[Agent Error] {payload.get('errorMessage')}")
                    else:
                        print(f"\n[Event: {event_name}] {json.dumps(payload)}")
                else:
                    print(f"\n[Raw Frame] {frame}")

            except json.JSONDecodeError:
                print(f"\n[Raw text received] {message}")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"\nConnection closed: {e}")
    except Exception as e:
        print(f"\nError receiving messages: {e}")

async def send_chat_message(websocket, prompt, session_key="global"):
    """Sends a chat request frame to the gateway."""
    req_id = str(uuid.uuid4())[:8]
    idempotency_key = str(uuid.uuid4())
    
    payload = {
        "type": "req",
        "id": req_id,
        "method": "chat.send",
        "params": {
            "sessionKey": session_key,
            "message": prompt,
            "idempotencyKey": idempotency_key
        }
    }
    
    print(f"\n[Sending Request {req_id}] Sending prompt: '{prompt}'...")
    await websocket.send(json.dumps(payload))

async def main():
    parser = argparse.ArgumentParser(description="OpenClaw WebSocket Client")
    parser.add_argument("--host", default="127.0.0.1", help="Gateway server host")
    parser.add_argument("--port", type=int, default=18789, help="Gateway server port")
    parser.add_argument("--token", default="", help="Gateway authorization token")
    parser.add_argument("--session", default="global", help="Session key (e.g. global, main)")
    args = parser.parse_args()

    # Construct the WebSocket endpoint.
    # OpenClaw supports authentication via a bearer token. We will pass it in the
    # headers when upgrading the connection.
    headers = {}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"

    url = f"ws://{args.host}:{args.port}/"
    print(f"Connecting to OpenClaw Gateway at {url}...")

    try:
        async with websockets.connect(url, extra_headers=headers) as websocket:
            print("Connected! Initializing handshake...")
            
            # 1. Perform protocol handshake
            handshake_id = "handshake-1"
            handshake = {
                "type": "req",
                "id": handshake_id,
                "method": "connect",
                "params": {
                    "minProtocol": 1,
                    "maxProtocol": 1,
                    "client": {
                        "id": "openclaw-python-client",
                        "displayName": "Python SDK Example",
                        "version": "1.0.0",
                        "platform": sys.platform,
                        "mode": "operator"
                    }
                }
            }
            await websocket.send(json.dumps(handshake))
            
            # Start background task to receive streaming answers
            receive_task = asyncio.create_task(receive_messages(websocket))
            
            print("\nHandshake sent. You can now type messages to talk to your OpenClaw agent.")
            print("Type '/exit' or '/quit' to close the connection.\n")
            
            # Simple interactive loop
            while True:
                loop = asyncio.get_event_loop()
                # Run input in executor so it doesn't block the async event loop
                user_input = await loop.run_in_executor(None, input, "You > ")
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                    
                if user_input in ("/exit", "/quit"):
                    print("Exiting...")
                    break
                
                await send_chat_message(websocket, user_input, session_key=args.session)
                # Give the streaming receiver a little time to catch up before showing the next prompt
                await asyncio.sleep(0.5)

            # Cancel background task before leaving
            receive_task.cancel()
            
    except Exception as e:
        print(f"Failed to connect or communicate: {e}", file=sys.stderr)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDisconnected.")
