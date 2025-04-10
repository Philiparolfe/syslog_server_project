import socket
import signal
import sys
import sqlite3
from datetime import datetime
import requests

URL = "http://192.168.100.11:8000/db_updated"  # Adjust if running on a different host/port



def create_db():
    """ Creates a database and log table if it doesn't exist """
    conn = sqlite3.connect('syslogs.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            source_ip TEXT,
            syslog_severity TEXT,
            log_message TEXT
        )
    ''')
    conn.commit()
    conn.close()

def insert_log(timestamp, source_ip, syslog_severity, log_message):
    """ Insert a log into the database """
    conn = sqlite3.connect('syslogs.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO logs (timestamp, source_ip, syslog_severity, log_message)
        VALUES (?, ?, ?, ?)
    ''', (timestamp, source_ip, syslog_severity, log_message))
    conn.commit()
    conn.close()

def parse_log(log_message):
    """ Parse syslog messages without using regex """
    try:
        # Remove enclosing angle brackets and split priority
        priority_part, remainder = log_message[1:].split('>', 1)
        priority = int(priority_part)

        # Calculate severity from priority
        severity = priority % 8

        # Remove message index (e.g., "43:")
        _, remainder = remainder.split(': ', 1)

        # Extract timestamp (after `*`)
        timestamp_part, remainder = remainder.split(': ', 1)

        # Extract syslog identifier (after `%`)
        syslog_part, message = remainder.split(': ', 1)

        return timestamp_part.strip(), severity, syslog_part.strip(), message.strip()
    
    except ValueError:
        return None, None, None, log_message  # Return original if parsing fails

def syslog_server(host='0.0.0.0', port=514):
    """ Simple Syslog server to collect logs from network devices """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    
    print(f"Listening for syslog messages on {host}:{port}...")
    
    def signal_handler(sig, frame):
        print("\nServer shutting down...")
        sock.close()
        sys.exit(0)
    
    # Register the signal handler for SIGINT (Ctrl + C)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create the database and table if they don't exist
    create_db()
    
    while True:
        data, addr = sock.recvfrom(1024)
        log_message = data.decode()
        source_ip = addr[0]
        received_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Parse the log message
        log_timestamp, syslog_severity, syslog_identifier, parsed_message = parse_log(log_message)

        # Use parsed timestamp if available, otherwise use the received time
        timestamp = log_timestamp if log_timestamp else received_timestamp

        # Save the parsed log to the database
        insert_log(timestamp, source_ip, syslog_severity, parsed_message)
        
        print(f"Log received from {source_ip}: {parsed_message}")
        response = requests.post(URL)
        if response.status_code == 200:
            print("Success:", response.json())
        else:
            print("Error:", response.status_code, response.text)

syslog_server()
