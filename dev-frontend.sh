#!/bin/bash

# Function to handle cleanup on exit
cleanup() {
    echo "Stopping services..."
    # Send SIGINT to both processes to gracefully stop them
    kill -INT $fastapi_pid
    kill -INT $dev_pid
    wait $fastapi_pid
    wait $dev_pid
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

sudo chown -R "$USER:$USER" syslog/


#syslog device config
python3 auto.py

if command -v npm &> /dev/null
then
    echo "npm is installed"
else
    echo "npm is not installed, installing..."
    sudo apt install nodejs -y
    sudo apt install npm -y
fi
cd frontend-dev/
npm install
npm run dev &
dev_pid=$!
wait $dev_pid


# Wait for both processes to finish (in this case, they should keep running)

wait $fastapi_pid

