#!/bin/bash

VENV_PATH="./.venv"
PYTHON="$VENV_PATH/bin/python"

SYSLOG_SCRIPT="syslog/syslog_server.py"
API_SCRIPT="api/main.py"

cleanup() {
    echo "Stopping services..."
    if [ -n "$syslog_pid" ] && ps -p $syslog_pid > /dev/null 2>&1; then
        kill -INT $syslog_pid
        wait $syslog_pid
    fi
    if [ -n "$fastapi_pid" ] && ps -p $fastapi_pid > /dev/null 2>&1; then
        kill -INT $fastapi_pid
        wait $fastapi_pid
    fi
    echo "Both services stopped."
}

trap cleanup SIGINT SIGTERM

run_as_root() {
    echo "Running $SYSLOG_SCRIPT as root using virtualenv..."
    "$PYTHON" "$SYSLOG_SCRIPT" &
    syslog_pid=$!
    
}

run_as_user() {
    if [ -n "$SUDO_USER" ]; then
        
        echo "Running $API_SCRIPT as regular user ($SUDO_USER) using virtualenv..."
        sudo -u "$SUDO_USER" "$PYTHON" "$API_SCRIPT" &
        fastapi_pid=$!
        
    else
        echo "Error: Cannot determine non-root user to run $API_SCRIPT safely."
        exit 1
    fi
}

main() {
    if [ ! -x "$PYTHON" ]; then
        echo "Error: Virtual environment not found or not executable at $PYTHON"
        echo "Hint: Run 'make install' first."
        exit 1
    fi

    if [ "$(id -u)" -eq 0 ]; then
        echo "Running script with root privileges."
        run_as_root
        run_as_user
        wait $syslog_pid
        wait $fastapi_pid
    else
        echo "Elevating to root for privileged operations..."
        sudo "$0" "$@"
        exit 0
    fi
}

main "$@"
