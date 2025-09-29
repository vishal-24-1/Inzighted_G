# 🛠 Backend Development Guide – Voice AI System

## ✅ 1. Overview

This backend handles:

1. Receiving audio streams from clients (WebRTC/WebSocket)
2. Forwarding audio to **Whisper STT** (self-hosted) for transcription
3. Sending transcripts to **Gemini LLM** for response generation
4. Converting LLM text responses to speech using **Google TTS**
5. Streaming audio chunks back to client for playback

> **Note:** All dependent credentials and endpoints (Whisper server URL, Gemini API key, Google TTS credentials) are provided. Placeholders are included where needed.

---

## ✅ 2. Components & Responsibilities

### 1. WebRTC/WebSocket Gateway
- Accepts client audio streams (PCM/Opus, 16kHz)
- Maintains session IDs and state
- Forwards audio to Whisper STT
- Receives TTS audio chunks from TTS adapter
- Streams audio back to client
- Handles control messages (pause, stop, barge-in)

### 2. Whisper STT Adapter
- Connects to **Whisper EC2 instance**
- Streams audio chunks to Whisper
- Receives **interim & final transcripts**
- Forwards transcripts to LLM adapter

**Placeholder:**
```text
WHISPER_SERVER_URL = "<WHISPER_STT_ENDPOINT>"

3. LLM Adapter – Gemini

-Sends transcript + conversation context to Gemini API

-Receives streaming text response

-Supports conversation memory, persona injection

Placeholder:

GEMINI_API_KEY = "<YOUR_GEMINI_API_KEY>"

4. Google TTS Adapter

-Converts LLM text responses to audio chunks (PCM/Opus)

-Supports streaming output to backend

-Optional: SSML for pauses, intonation, multi-language

Placeholder:

GOOGLE_TTS_CREDENTIALS = "<GOOGLE_SERVICE_ACCOUNT_JSON>"

5. Audio Orchestrator

-Receives TTS audio chunks

-Handles small jitter buffer (~100–200ms)

-Injects audio into outgoing WebRTC/WebSocket track

-Implements barge-in: stops TTS if user starts speaking

✅ 3. Data Flow (Backend Focused)
Client Audio → Backend Gateway → Whisper STT → Transcript
Transcript → Gemini LLM → Text Response → Google TTS → Audio Chunks → Client Playback


Flow Steps:

-Receive audio chunk from client (WebRTC/WebSocket)

-Forward chunk to Whisper STT

-Receive interim/final transcript

-Send transcript to Gemini LLM

-Receive streaming text response

-Send text to Google TTS for audio synthesis

-Stream audio chunks to client

✅ 4. Latency Targets
Stage	Target
Mic → Backend	< 50 ms
Whisper STT	< 300 ms
Gemini Response Start	< 300–500 ms
Google TTS Start	< 200 ms
Playback Start	< 150 ms
Total	600–900 ms

✅ 5. Backend Implementation Notes

Session Management

-Each client session has a unique session ID

-Maintain conversation context for Gemini LLM

Streaming

-Send audio in 20–40ms frames to Whisper STT

-Stream LLM tokens to TTS adapter as they arrive

-Stream audio chunks back to client with minimal buffer

-Placeholders / Config

-WHISPER_SERVER_URL → Whisper STT endpoint

-GEMINI_API_KEY → Gemini API key

-GOOGLE_TTS_CREDENTIALS → Google Cloud service account JSON

Optional Enhancements

-Barge-in detection (pause TTS if user speaks)

-Interim transcripts displayed to client

-Multi-language TTS support

✅ 6. Deliverables for Agent

-The AI agent should generate:

-WebRTC/WebSocket backend code

-Audio input/output streaming

-Session management

-Whisper STT Adapter

-Streaming audio → transcript

-Gemini LLM Adapter

-Sending transcript → receiving text response

-Google TTS Adapter

-Sending text → streaming audio chunks

-Audio Orchestrator

-Buffering & playback to client

-Barge-in handling

-Config placeholders

  -Easy replacement of Whisper URL, Gemini API key, and Google credentials