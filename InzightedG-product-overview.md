# 🧠 InzightEd G — Product Flow Guide (For LLM Agent)
One-line summary:
InzightedG - A voice-first evaluator: user logs in → uploads raw study material → system ingests + builds a RAG vector DB (server.db in your pinecone DB) → user starts a short, low-latency bidirectional audio conversation grounded to the RAG data → on session end the transcript + context are sent to the LLM which synthesizes a SWOT, confidences, 1–3 focus actions and a 20-min micro-plan.

This document explains the end-to-end product flow to help you understand the system before implementation.  

---

For this product:

- **Backend:** Django  
- **Frontend:** React with TypeScript  
- **Database / Storage:** Refer to `RAG.md` for document storage  
- **Voice Pipeline:** Real-time STT & TTS as per `Voice AI Architecture.md`  
- **LLM Integration:** Used for post-session insight generation


## ✅ 1. User Login
The user logs into the platform to access the product (JWT Sessions, Auth).

---

## ✅ 2. Upload Learning Material
The user uploads documents only:

- PDF
- Word files (DOC / DOCX)

After upload, the system processes the files and prepares them for retrieval.

**Reference:**  
👉 See `RAG.md` for handling:  
- Document ingestion  
- Vector embedding  
- Storage (e.g., `server.db`)  

---

## ✅ 3. Start a Voice Conversation
- The user provides a Topic for the conversation session.  
- The user starts speaking to the system.  

A real-time, low-latency, bidirectional voice conversation takes place.  
System responses are grounded in the uploaded documents (RAG data).

**Reference:**  
👉 See `voice-ai-architecture.md` for:  
- Speech-to-Text  
- Text-to-Speech  
- Latency handling  
- Real-time streaming logic  

---

## ✅ 4. Active Session (Approx. 10 Minutes)
During the session:

- The user speaks naturally.  
- The system interprets and responds using the processed documents.  
- No manual typing is required.  
- The session continues until it naturally ends or the user stops.

---

## ✅ 5. Post-Session Insight Generation
Once the session ends:

- The entire conversation transcript is collected.  
- The transcript is passed to the LLM.  
- The LLM generates structured insights, including:
  - Strengths
  - Weaknesses
  - Opportunities / Action Points
  - Other analytical takeaways
- Gemini LLM API is used for this process
These insights are shown to the user in the UI.

---

## ✅ 6. Session Completion
After insights are displayed, the user may:

- Review the results  
- Save or exit  
- Start a new conversation

---

## ✅ End of Flow
This is the complete product journey — from login to insight delivery — with clear separation of concerns.
