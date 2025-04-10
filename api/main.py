from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import logging
import uvicorn


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

status_flag = False  # Change this to True or False to control the message

# Root endpoint
@app.get("/", response_model=MessageResponse)
def read_root():
    return {"message": "Welcome to the FastAPI syslog service."}

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
    await websocket.accept()
    try:
        while True:
            
            if status_flag:
                message = "Status is True"
                await websocket.send_text(message)
                if status_flag == True:
                    status_flag = False  
            else:
                message = "Status is False"
                #await websocket.send_text(message)
            await asyncio.sleep(4)  # Send update every 2 seconds
    except WebSocketDisconnect:
        print("Client disconnected")

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
def clear_logs():
    global status_flag
    
    try:
        with sqlite3.connect(DB_FILE_PATH) as conn:
            cursor = conn.cursor()

            # Delete all logs
            cursor.execute("DELETE FROM logs")
            conn.commit()

        logger.info("All logs cleared successfully.")
        status_flag = True
        return MessageResponse(message="All logs cleared successfully.")

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def run():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    run()