from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
from sqlmodel import Session
import pandas as pd

from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from chatbot_openai import OpenAIChatbot  # reuse your bot class
from db import init_db, get_session, Message

# Create FastAPI app
app = FastAPI()

@app.on_event("startup")
def on_startup():
    # create tables when the app starts
    init_db()


# Create a single bot instance to keep conversation history
bot = OpenAIChatbot(name="MilliBot", model="gpt-4o-mini")


# ---------- API models ----------
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


# ---------- Routes ----------

@app.get("/", response_class=HTMLResponse)
async def get_home():
    """
    Serve a simple HTML page with a chat UI.
    """
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <title>MilliBot Chat</title>
        <style>
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }
            body {
                background: #0f172a;
                color: #e5e7eb;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 16px;
            }
            .chat-wrapper {
                width: 100%;
                max-width: 800px;
                background: #020617;
                border-radius: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.7);
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            .chat-header {
                padding: 16px 20px;
                border-bottom: 1px solid #1f2937;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .chat-header-avatar {
                width: 32px;
                height: 32px;
                border-radius: 999px;
                background: linear-gradient(135deg, #38bdf8, #a855f7);
            }
            .chat-header-text {
                display: flex;
                flex-direction: column;
            }
            .chat-header-text strong {
                font-size: 16px;
            }
            .chat-header-text span {
                font-size: 12px;
                color: #9ca3af;
            }
            .chat-log {
                flex: 1;
                padding: 16px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
            .msg {
                max-width: 75%;
                padding: 10px 14px;
                border-radius: 16px;
                font-size: 14px;
                line-height: 1.4;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .msg-user {
                align-self: flex-end;
                background: #1d4ed8;
                color: #e5e7eb;
                border-bottom-right-radius: 4px;
            }
            .msg-bot {
                align-self: flex-start;
                background: #111827;
                border-bottom-left-radius: 4px;
                border: 1px solid #1f2937;
            }
            .chat-input-row {
                padding: 10px;
                border-top: 1px solid #1f2937;
                display: flex;
                gap: 8px;
                background: #020617;
            }
            .chat-input-row input {
                flex: 1;
                padding: 10px 12px;
                border-radius: 999px;
                border: 1px solid #374151;
                background: #020617;
                color: #e5e7eb;
                outline: none;
                font-size: 14px;
            }
            .chat-input-row input:focus {
                border-color: #60a5fa;
            }
            .chat-input-row button {
                padding: 0 18px;
                border-radius: 999px;
                border: none;
                font-size: 14px;
                cursor: pointer;
                background: linear-gradient(135deg, #38bdf8, #a855f7);
                color: white;
                transition: transform 0.05s ease, box-shadow 0.1s ease;
            }
            .chat-input-row button:active {
                transform: translateY(1px);
                box-shadow: none;
            }
            .status {
                font-size: 12px;
                color: #9ca3af;
                padding: 4px 16px 8px 16px;
            }
        </style>
    </head>
    <body>
        <div class="chat-wrapper">
            <div class="chat-header">
                <div class="chat-header-avatar"></div>
                <div class="chat-header-text">
                    <strong>MilliBot</strong>
                </div>
            </div>
            <div id="chatLog" class="chat-log">
                <div class="msg msg-bot">
                    Hey, I'm MilliBot. Ask me anything!
                </div>
            </div>
            <div style="padding: 8px 16px; border-top: 1px solid #1f2937; border-bottom: 1px solid #1f2937; background:#020617;">
                <label style="font-size: 12px; color:#9ca3af; margin-right: 8px;">
                    Upload .txt or Excel file:
                </label>
                <input id="fileInput" type="file" accept=".txt,.xlsx,.xls" style="font-size: 12px; color:#e5e7eb;">
                <button id="uploadButton" style="margin-left: 8px; padding: 4px 12px; border-radius:999px; border:none; font-size:12px; cursor:pointer; background:#374151; color:#e5e7eb;">
                    Upload
                </button>
                <div id="uploadResult" style="margin-top: 4px; font-size: 11px; color:#9ca3af;"></div>
            </div>
            <div class="status" id="status"></div>
            <div class="chat-input-row">
                <input
                    id="messageInput"
                    type="text"
                    placeholder="Type a message and press Enter..."
                    autocomplete="off"
                />
                <button id="sendButton">Send</button>
            </div>
        </div>

        <script>
            const chatLog = document.getElementById("chatLog");
            const input = document.getElementById("messageInput");
            const sendButton = document.getElementById("sendButton");
            const statusEl = document.getElementById("status");
            const fileInput = document.getElementById("fileInput");
            const uploadButton = document.getElementById("uploadButton");
            const uploadResult = document.getElementById("uploadResult");


            function appendMessage(text, isUser) {
                const div = document.createElement("div");
                div.classList.add("msg");
                div.classList.add(isUser ? "msg-user" : "msg-bot");
                div.textContent = text;
                chatLog.appendChild(div);
                chatLog.scrollTop = chatLog.scrollHeight;
            }

            async function sendMessage() {
                const text = input.value.trim();
                if (!text) return;

                appendMessage(text, true);
                input.value = "";
                statusEl.textContent = "MilliBot is thinking...";

                try {
                    const res = await fetch("/chat", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                        },
                        body: JSON.stringify({ message: text }),
                    });

                    if (!res.ok) {
                        throw new Error("Request failed with status " + res.status);
                    }

                    const data = await res.json();
                    appendMessage(data.reply, false);
                } catch (err) {
                    appendMessage("Error talking to server: " + err.message, false);
                } finally {
                    statusEl.textContent = "";
                }
            }

            async function uploadFile() {
                const file = fileInput.files[0];
                if (!file) {
                    uploadResult.textContent = "No file selected.";
                    return;
                }

                uploadResult.textContent = "Uploading and processing file...";

                const formData = new FormData();
                formData.append("file", file);

                try {
                    const res = await fetch("/upload", {
                        method: "POST",
                        body: formData,
                    });

                    if (!res.ok) {
                        const text = await res.text();
                        throw new Error(text || ("Upload failed with status " + res.status));
                    }

                    const data = await res.json();
                    uploadResult.textContent = "Upload ok. Preview: " + data.preview_summary;
                } catch (err) {
                    uploadResult.textContent = "Error: " + err.message;
                }
            }

            uploadButton.addEventListener("click", uploadFile);


            sendButton.addEventListener("click", sendMessage);
            input.addEventListener("keydown", (e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    sendMessage();
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session: Session = Depends(get_session),
):
    """
    Receive a message from the frontend, get a reply from the bot,
    save both to the database, and return the reply.
    """
    user_text = request.message
    reply = bot.generate_reply(user_text)
    bot.history.append((user_text, reply))

    # For now, we use a fixed session_id.
    # Later you can generate a random ID per user and store it in a cookie.
    session_id = "anonymous"

    # Save user message
    user_msg = Message(
        session_id=session_id,
        role="user",
        content=user_text,
    )
    session.add(user_msg)

    # Save bot reply
    bot_msg = Message(
        session_id=session_id,
        role="assistant",
        content=reply,
    )
    session.add(bot_msg)

    session.commit()

    return ChatResponse(reply=reply)

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
):
    """
    Accept a file upload (.txt or Excel), parse it a bit,
    and return a small preview summary.
    """
    filename = file.filename or ""
    lower = filename.lower()

    if not filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Handle .txt files
    if lower.endswith(".txt"):
        content_bytes = await file.read()
        try:
            text = content_bytes.decode("utf-8", errors="ignore")
        except Exception:
            raise HTTPException(status_code=400, detail="Could not decode text file")

        # Take only the first X characters as a preview
        preview = text[:200]
        if len(text) > 200:
            preview += "... (truncated)"

        return {
            "filename": filename,
            "file_type": "text",
            "preview_summary": preview,
        }

    # Handle Excel files (.xlsx / .xls)
    if lower.endswith(".xlsx") or lower.endswith(".xls"):
        # For safety, reset file pointer before pandas reads it
        file.file.seek(0)
        try:
            df = pd.read_excel(file.file)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error reading Excel file: {e}")

        # Build a tiny preview: number of rows/cols + first few column names
        rows, cols = df.shape
        col_names = list(df.columns.astype(str))[:5]
        preview = f"Excel sheet with {rows} rows and {cols} columns. First columns: {col_names}"

        return {
            "filename": filename,
            "file_type": "excel",
            "preview_summary": preview,
        }

    # Unsupported extension
    raise HTTPException(status_code=400, detail="Only .txt and .xlsx/.xls files are supported")

