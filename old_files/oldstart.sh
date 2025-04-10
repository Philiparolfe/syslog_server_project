#!/bin/bash

# Function to handle cleanup on exit
cleanup() {
    echo "Stopping services..."
    # Send SIGINT to both processes to gracefully stop them
    kill -INT $syslog_pid
    kill -INT $fastapi_pid
    wait $syslog_pid
    wait $fastapi_pid
    echo "Both services stopped."
    cd ..
    #deactivate
}

# Trap SIGINT (Ctrl+C) to ensure cleanup is called when exiting
trap cleanup SIGINT
# install dependancies
pip install -r requirements.txt

# start auto.py
python3 auto.py
# Start the syslog server with sudo privileges and capture its process ID
echo "Starting syslog server..."
sudo python3 syslog_server.py &
syslog_pid=$!

# Start the FastAPI webserver and capture its process ID
#s.. .venv/bin/activate
cd api/
echo "Starting FastAPI webserver..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
fastapi_pid=$!

# Wait for both processes to finish (in this case, they should keep running)
wait $syslog_pid
wait $fastapi_pid
