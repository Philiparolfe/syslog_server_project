import { Grid, html } from "gridjs";
import "gridjs/dist/theme/mermaid.css";

let gridInstance = null;

//let apiAddress = "http://localhost:8000/"; //<-- for development
let apiAddress = "/"; //<--- for production
let wsAddress; //"ws://192.168.100.11:8000/ws";



function fetchLogs() {
  return fetch(`${apiAddress}logs`)
    .then(res => res.json())
    .then(data => data.logs.map(log => [
      log.id,
      log.timestamp,
      log.source_ip,
      log.severity, // This should be a number, like 1, 2, 3, etc.
      log.log_message
    ]));
}

async function renderGrid(severityFilter = "") {
  const wrapper = document.getElementById("wrapper");

  // Ensure the wrapper is empty before rendering the grid again
  wrapper.innerHTML = ""; // Clear the container
  
  // Check if there's an existing gridInstance and destroy it
  if (gridInstance) {
    gridInstance.destroy(); // Destroy the previous instance to avoid errors
  }

  let logs = await fetchLogs();

  if (severityFilter !== "") {
    const severityInt = parseInt(severityFilter, 10);
    logs = logs.filter(row => parseInt(row[3], 10) === severityInt); // Filter by severity
  }

  gridInstance = new Grid({
    columns: [
      'ID', 
      'Time Stamp', 
      'Source IP', 
      'Severity',
      'Log Message',
      {
        name: "Actions",
        formatter: (cell, row) => {
          return html(`
            <button class="delete-btn" data-id="${row.cells[0].data}" onclick="deleteLog(${row.cells[0].data})">Delete</button>
          `);
        }
      }
    ],
    data: logs,
    pagination: true,
    search: true,
    sort: true,
  }).render(wrapper); // Render the grid to the wrapper
}

let pollingInterval;

function startPolling() {
  pollingInterval = setInterval(() => {
    console.log("📡 Polling for new logs...");
    const severity = document.getElementById("severityFilter").value;
    renderGrid(severity); // Re-render with current filter
  }, 10000); // every 10 seconds
}

let ws;
let reconnectAttempts = 0;
const maxReconnects = 5;
const reconnectDelay = 3000; // 3 seconds

function connectWebSocket() {
  fetch(`${apiAddress}config/ws-url`)
  .then(response => response.json())
  .then(data => {
    const wsAddress = data.websocket_ip || 'ws://localhost:8000/ws'; // Default to localhost if not set
    const ws = new WebSocket(wsAddress);

    ws.onopen = () => {
      console.log('WebSocket connected to:', wsAddress);
      renderGrid()
    };

    ws.onmessage = (event) => {
      console.log('New log message:', event.data);
      renderGrid()
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed');
      alert("WebSocket connection closed")
    };
  })
  .catch(error => {
    console.error('Error fetching WebSocket URL:', error);
  });
}

connectWebSocket(); // Establish WebSocket connection on page load

document.getElementById("severityFilter").addEventListener("change", function () {
  const selectedSeverity = this.value;  // Get the selected value from dropdown
  renderGrid(selectedSeverity);         // Re-render the grid with the new filter
});

function deleteLog(logID) {
  fetch(`${apiAddress}logs/${logID}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
  })
  .then(response => {
    if (!response.ok) {
      return response.json().then(data => {
        throw new Error(data.detail || 'Failed to delete log');
      });
    }
    return response.json();
  })
  .then(data => {
    console.log('Log deleted successfully:', data.message);
    renderGrid(document.getElementById("severityFilter").value); // re-render with current filter
  })
  .catch(error => {
    console.error('Error:', error.message);
  });
}

// Initial render on page load
//renderGrid();  // Initial call to render the grid with no filter
