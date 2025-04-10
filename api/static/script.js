
async function getData() {
    const url = "http://192.168.100.11:8000/logs";
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Response status: ${response.status}`);
        }

        const data = await response.json();
        console.log("Fetched Logs:", data);

        // Update the table with logs
        populateTable(data.logs);
    } catch (error) {
        console.error("Error fetching logs:", error.message);
    }
}

function populateTable(logs) {
    const tableBody = document.querySelector("#logsTable tbody");
    tableBody.innerHTML = "";  // Clear previous entries

    logs.forEach(log => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${log.id}</td>
            <td>${log.timestamp}</td>
            <td>${log.source_ip}</td>
            <td>${log.severity}</td>
            <td>${log.log_message}</td>
        `;
        tableBody.appendChild(row);
    });
}

// Fetch logs when the page loads
getData();

// WebSocket connection to FastAPI
const ws = new WebSocket("ws://192.168.100.11:8000/ws");

ws.onopen = () => {
    console.log("Connected to WebSocket!");
};

ws.onmessage = (event) => {
    console.log("Event data:", event.data);
    getData();  // Re-fetch logs when an update occurs
};

ws.onerror = (error) => {
    console.error("WebSocket error:", error);
};

ws.onclose = () => {
    console.log("WebSocket connection closed.");
};

let sortDirections = [true, true, true, true, true]; // Track sorting direction for each column (true = ascending, false = descending)

function sortTable(columnIndex) {
    const table = document.getElementById("logsTable");
    const rows = Array.from(table.rows).slice(1); // Skip the header row
    const isNumeric = columnIndex === 0 || columnIndex === 1; // ID and Timestamp columns are numeric

    // Toggle the sorting direction for the clicked column
    sortDirections[columnIndex] = !sortDirections[columnIndex];

    rows.sort((rowA, rowB) => {
        const cellA = rowA.cells[columnIndex].innerText;
        const cellB = rowB.cells[columnIndex].innerText;

        if (isNumeric) {
            // Convert to number for sorting if numeric
            return sortDirections[columnIndex] ? parseFloat(cellA) - parseFloat(cellB) : parseFloat(cellB) - parseFloat(cellA);
        } else {
            // Otherwise sort as strings
            return sortDirections[columnIndex] ? cellA.localeCompare(cellB) : cellB.localeCompare(cellA);
        }
    });

    // Reorder the rows in the table
    rows.forEach(row => table.appendChild(row));
}







