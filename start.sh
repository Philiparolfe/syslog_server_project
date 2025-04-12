#!/bin/bash

# Function to handle cleanup on exit
cleanup() {
    echo "Stopping services..."
    # Send SIGINT to both processes to gracefully stop them
    kill -INT $syslog_pid
    kill -INT $fastapi_pid
    wait $syslog_pid
    wait $fastapi_pid
    deactivate
    echo "Both services stopped."
}

# Trap SIGINT (Ctrl+C) to ensure cleanup is called when exiting
trap cleanup SIGINT

sudo apt install python3-venv -y
sudo apt install python3-pip -y


# Check if virtual environment exists, if not creates one
if [ ! -d ".venv/" ]; then
    echo "Virtual environment not found. Creating virtual environment..."
    python3 -m venv ".venv/"
fi

# Activate the virtual environment
. .venv/bin/activate

# Install dependencies from requirements.txt
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "requirements.txt not found. Skipping dependency installation."
fi

sleep 10

cd api/
echo "Starting FastAPI webserver..."
python3 main.py &
fastapi_pid=$!
cd ..

sleep 3
echo "______"
echo "syslog server requires elevated privileges to use port 514. Enter password if required:"
echo "______"


cd syslog/
sudo python3 syslog_server.py &
syslog_pid=$!


sleep 3

cd ..
sudo chown -R "$USER:$USER" syslog/


#syslog device config
python3 auto.py


# Wait for both processes to finish (in this case, they should keep running)
wait $syslog_pid
wait $fastapi_pid
