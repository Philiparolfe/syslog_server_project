from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import logging
import uvicorn
from user_handler import UserManager
import secrets
import os
from itsdangerous import URLSafeSerializer

web_key_path = "web.key"
# Check if key already exists
if os.path.exists(web_key_path):
    print(f"Web key already exists at '{web_key_path}'.")
    with open(web_key_path, "r") as f:
        web_key = f.read().strip()
else:
    # Generate and save new key
    web_key = secrets.token_urlsafe(32)
    with open(web_key_path, "w") as f:
        f.write(web_key)
    print(f"New Web key generated and saved to '{web_key_path}'. (for session authentication\n)")

WEB_KEY = web_key 
COOKIE_NAME = "session"
serializer = URLSafeSerializer(WEB_KEY)

# Get current user from cookie
def get_current_user(request: Request):
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return None
    try:
        data = serializer.loads(cookie)
        return data.get("username")
    except Exception:
        return None

# Initialize FastAPI app
app = FastAPI()
#app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/dist", StaticFiles(directory="dist"), name="dist")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to restrict allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database file path
DB_FILE_PATH = "../syslog/syslogs.db"

# Pydantic Models
class Log(BaseModel):
    id: int
    timestamp: str
    source_ip: str
    severity: int
    log_message: str

class LogsResponse(BaseModel):
    logs: List[Log]

class MessageResponse(BaseModel):
    message: str

class ConfigResponse(BaseModel):
    websocket_ip: str

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")

manager = ConnectionManager()


status_flag = False  # Change this to True or False to control the message

def insert_log(timestamp, source_ip, syslog_severity, log_message):
    """ Insert a log into the database """
    conn = sqlite3.connect(DB_FILE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO logs (timestamp, source_ip, syslog_severity, log_message)
        VALUES (?, ?, ?, ?)
    ''', (timestamp, source_ip, syslog_severity, log_message))
    conn.commit()
    conn.close()


# Root endpoint
@app.get("/")
def read_root(user: str = Depends(get_current_user)):
    #return {"message": "Welcome to the FastAPI syslog service."}
    if not user:
        #raise HTTPException(status_code=401, detail="Not logged in")
        return RedirectResponse(url="/dist/login.html")
    return RedirectResponse(url="/dist/index.html")

@app.post("/login")
def login(response: Response, username: str = Form(...), password: str = Form(...)):
    user_manager = UserManager("../syslog/users.db")  
    if not user_manager.auth_user(username, password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user_manager.close()
    
    # Create signed cookie
    signed_data = serializer.dumps({"username": username})
    response = RedirectResponse(url="/protected", status_code=302)
    response.set_cookie(COOKIE_NAME, signed_data, httponly=True, max_age=3600)
    return response

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie(COOKIE_NAME)
    return response

@app.get("/is_logged_in", response_model=bool)
def is_logged_in(user: str = Depends(get_current_user)):
    return user is not None

@app.get("/protected")
def protected(user: str = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return {"message": f"Hello {user}, you are logged in!"}

@app.get("/config/ws-url", response_model=ConfigResponse)
def get_ws_url():
    try:
        conn = sqlite3.connect(DB_FILE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT websocket_ip FROM config LIMIT 1")
        result = cursor.fetchone()
        conn.close()

        if result:
            return ConfigResponse(websocket_ip=result[0])
        else:
            raise HTTPException(status_code=404, detail="WebSocket IP not found in config.")

    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/db_updated")
async def set_status_true():
    global status_flag
    if status_flag == False:
        status_flag = True
    return {"message": "status_flag is set to True"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global status_flag  
    await manager.connect(websocket)
    try:
        while True:
            if status_flag:
                await manager.broadcast("Status is True")
                status_flag = False
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected")
    except asyncio.CancelledError:
        print("WebScocket task cancelled!")

# Fetch all logs
@app.get("/logs", response_model=LogsResponse)
def read_logs():
    try:
        with sqlite3.connect(DB_FILE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, timestamp, source_ip, syslog_severity, log_message FROM logs ORDER BY timestamp DESC;")
            rows = cursor.fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail="No logs found in the database.")

        logs = [Log(id=row[0], timestamp=row[1], source_ip=row[2], severity=row[3], log_message=row[4]) for row in rows]
        return {"logs": logs}

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/logs/recent", response_model=LogsResponse)
def get_most_recent_log():
    try:
        with sqlite3.connect(DB_FILE_PATH) as conn:
            cursor = conn.cursor()

            # Query the most recent log by timestamp
            cursor.execute("SELECT id, timestamp, source_ip, syslog_severity, log_message FROM logs ORDER BY timestamp DESC LIMIT 1")
            log = cursor.fetchone()

            if not log:
                raise HTTPException(status_code=404, detail="No logs found.")

        # Return the most recent log wrapped in a list (since LogsResponse expects a list)
        return LogsResponse(logs=[Log(id=log[0], timestamp=log[1], source_ip=log[2], severity=log[3], log_message=log[4])])

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Fetch logs by severity
@app.get("/logs/severity/{level}", response_model=LogsResponse)
def filter_logs_by_severity(level: int):
    if level < 1 or level > 5:
        raise HTTPException(status_code=400, detail="Severity level must be between 1 and 5.")

    try:
        with sqlite3.connect(DB_FILE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, timestamp, source_ip, syslog_severity, log_message FROM logs WHERE syslog_severity = ?", (level,))
            rows = cursor.fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail=f"No logs found with severity level {level}.")

        logs = [Log(id=row[0], timestamp=row[1], source_ip=row[2], severity=row[3], log_message=row[4]) for row in rows]
        return {"logs": logs}

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Delete a log entry
@app.delete("/logs/{log_id}", response_model=MessageResponse)
def delete_log(log_id: int):
    global status_flag
    try:
        with sqlite3.connect(DB_FILE_PATH) as conn:
            cursor = conn.cursor()

            # Check if log exists
            cursor.execute("SELECT * FROM logs WHERE id = ?", (log_id,))
            log = cursor.fetchone()

            if not log:
                raise HTTPException(status_code=404, detail=f"Log with ID {log_id} not found.")

            # Delete log
            cursor.execute("DELETE FROM logs WHERE id = ?", (log_id,))
            conn.commit()

        logger.info(f"Log {log_id} deleted successfully.")
        if status_flag == False:
            status_flag = True
        return {"message": f"Log with ID {log_id} deleted successfully."}

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.delete("/clearlogs", response_model=MessageResponse)
def clear_logs(request: Request):
    global status_flag
    now = datetime.now()
    formatted_timestamp = f"{now.strftime('%b %d %H:%M:%S')}.{now.microsecond // 1000:03d}"

    # Get client IP (accounting for proxies if needed)
    x_forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = x_forwarded_for.split(",")[0] if x_forwarded_for else request.client.host

    try:
        with sqlite3.connect(DB_FILE_PATH) as conn:
            cursor = conn.cursor()

            # Delete all logs
            cursor.execute("DELETE FROM logs")
            conn.commit()

        logger.info(f"All logs cleared successfully by {client_ip}.")
        insert_log(
            timestamp=formatted_timestamp,
            source_ip=client_ip,
            syslog_severity="4",
            log_message="All logs cleared via web dashboard."
        )
        status_flag = True
        return MessageResponse(message="All logs cleared successfully.")

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/register")
async def register(
    admin_user: str = Form(...),
    admin_password: str = Form(...),
    user: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...)
):
    user_manager = UserManager("../syslog/users.db")
    if user_manager.auth_user(admin_user, admin_password):
        user_manager.add_user(username=user, password=password, phone=phone, email=email)
        return {
            "message": f"User '{user}' registered successfully by admin '{admin_user}'",
            "user_info": {
                "username": user,
                "email": email,
                "phone": phone
            }
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")


def run():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    run()