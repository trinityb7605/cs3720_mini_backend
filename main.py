# ----- mob08 server.py + additions -----
import os, uuid
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List

app = FastAPI()

# CORS is only for HTTP, not WS, but fine to keep
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload Folder & Static File Serving
UPLOAD_DIR = "/tmp/uploads" 
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/images", StaticFiles(directory=UPLOAD_DIR), name="images")

@app.get("/")
async def root():
    return {"message": "FastAPI WebSocket chat server is running"}

# AI-assisted (Claude, Oct 2026): /upload-photo, /photos, and /images mount
# HTTP Endpoints
@app.post("/upload-photo")
async def upload_photo(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(await file.read())
    print(f"Saved file: {filename}")   # shows up in Render logs
    return {
        "filename": filename,
        "url": f"/images/{filename}",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/photos")
async def list_photos():
    names = os.listdir(UPLOAD_DIR)
    names.sort(key=lambda n: os.path.getmtime(os.path.join(UPLOAD_DIR, n)), reverse=True)
    return [{"filename": n, "url": f"/images/{n}"} for n in names]

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        # Send the message to all connected clients
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception as e:
                print("Error sending to a client:", e)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received from client: {data}")

            # Broadcast whatever text we got (we'll send JSON from the frontend)
            await manager.broadcast(data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print("Unexpected error in websocket:", e)
        manager.disconnect(websocket)
        try:
            await websocket.close()
        except:
            pass
