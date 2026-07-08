import { useCallback, useEffect, useState } from "react";
import { DataGrid } from "@mui/x-data-grid";

const API_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

function Dashboard({ session, onOpenAdmin, onLogout }) {
  const [columns, setColumns] = useState([]);
  const [editableColumns, setEditableColumns] = useState([]);
  const [addableColumns, setAddableColumns] = useState([]);
  const [canAddRows, setCanAddRows] = useState(false);
  const [rows, setRows] = useState([]);
  const [months, setMonths] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState("");
  const [entryDates, setEntryDates] = useState([]);
  const [selectedEntryDate, setSelectedEntryDate] = useState("");
  const [newRow, setNewRow] = useState({});
  const [saving, setSaving] = useState({});
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const loadReport = useCallback(async function loadReport() {
    setLoading(true);
    setMessage("");

    try {
      const params = new URLSearchParams({ username: session.username });
      if (selectedMonth) params.set("month", selectedMonth);
      if (selectedEntryDate) params.set("entryDate", selectedEntryDate);

      const response = await fetch(`${API_URL}/report?${params.toString()}`);
      const data = await response.json();

      if (!response.ok || data.error) {
        setMessage(data.error || "Unable to load report");
        return;
      }

      setColumns(data.columns || []);
      setEditableColumns(data.editableColumns || []);
      setAddableColumns(data.addableColumns || []);
      setCanAddRows(Boolean(data.canAddRows));
      setRows(data.rows || []);
      setMonths(data.months || []);
      setEntryDates(data.entryDates || []);
    } catch (error) {
      setMessage("Backend is not reachable. Start the backend on port 8000.");
    } finally {
      setLoading(false);
    }
  }, [selectedEntryDate, selectedMonth, session.username]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  async function updateCell(rowId, field, value) {
    const row = rows.find((item) => item.id === rowId);
    if (!row || row[field] === value) {
      return row;
    }

    const cellKey = `${rowId}-${field}`;
    setSaving((prev) => ({ ...prev, [cellKey]: true }));
    setMessage("");

    const body = {
      field,
      value,
      version: row.version,
      username: session.username,
    };

    try {
      const response = await fetch(`${API_URL}/report/${rowId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(data.error || data.detail || "Unable to update cell");
      }

      const updatedRow = {
        ...row,
        ...(data.row || {}),
        version: data.row?.version ?? data.version ?? row.version,
      };

      setRows((prevRows) =>
        prevRows.map((r) =>
          r.id === rowId ? updatedRow : r
        )
      );
      return updatedRow;
    } catch (error) {
      setMessage(error.message || "Update failed. Check backend connection.");
      throw error;
    } finally {
      setSaving((prev) => {
        const updated = { ...prev };
        delete updated[cellKey];
        return updated;
      });
    }
  }

  async function processRowUpdate(newRow, oldRow) {
    const changedField = editableColumns.find((field) => newRow[field] !== oldRow[field]);

    if (!changedField) {
      return oldRow;
    }

    return updateCell(oldRow.id, changedField, newRow[changedField]);
  }

  async function addNewRow(event) {
    event.preventDefault();
    setSaving((prev) => ({ ...prev, new: true }));
    setMessage("");

    try {
      const response = await fetch(`${API_URL}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: session.username,
          rowData: newRow,
        }),
      });

      const data = await response.json();

      if (!response.ok || data.error) {
        setMessage(data.error || "Unable to add row");
        return;
      }

      setNewRow({});
      await loadReport();
      setMessage("Row added successfully");
    } catch (error) {
      setMessage("Add failed. Check backend connection.");
    } finally {
      setSaving((prev) => {
        const updated = { ...prev };
        delete updated.new;
        return updated;
      });
    }
  }

  async function downloadData() {
    setMessage("");

    try {
      const params = new URLSearchParams({ username: session.username });
      if (selectedMonth) params.set("month", selectedMonth);
      if (selectedEntryDate) params.set("entryDate", selectedEntryDate);

      const response = await fetch(`${API_URL}/export?${params.toString()}`);

      if (!response.ok) {
        setMessage("Unable to download data");
        return;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;

      const filename =
        response.headers
          .get("content-disposition")
          ?.split("filename=")[1]
          ?.replace(/"/g, "") || `report_${session.username}_${selectedMonth || selectedEntryDate || "all"}.csv`;

      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      setMessage("Data downloaded successfully");
    } catch (error) {
      setMessage("Download failed. Check backend connection.");
    }
  }

  const dataGridColumns = columns.map((col) => ({
    field: col.field,
    headerName: col.headerName,
    width: 150,
    editable: editableColumns.includes(col.field),
  }));

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">LR Portal</p>
          <h1>Report</h1>
        </div>
        <div className="session-actions">
          <span>{session.username}</span>
          {session.role === "Admin" && (
            <button type="button" onClick={onOpenAdmin}>
              Admin Users
            </button>
          )}
          <button
            type="button"
            onClick={loadReport}
            disabled={loading}
            title="Refresh the report data"
          >
            Refresh
          </button>
          <button
            type="button"
            onClick={downloadData}
            disabled={loading}
            title="Download visible data as CSV based on your column access"
          >
            Download Data
          </button>
          <button type="button" onClick={onLogout}>
            Logout
          </button>
        </div>
      </header>

      <section>
        {message && (
          <p className={message.includes("success") ? "success" : "error"}>
            {message}
          </p>
        )}

        <div className="report-controls">
          <label>
            Filter by Month:
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
            >
              <option value="">All Months</option>
              {months.map((month) => (
                <option key={month} value={month}>
                  {month}
                </option>
              ))}
            </select>
          </label>
          <label>
            Date of Entry:
            <input
              type="date"
              value={selectedEntryDate}
              onChange={(e) => setSelectedEntryDate(e.target.value)}
              list="entry-date-options"
            />
            <datalist id="entry-date-options">
              {entryDates.map((entryDate) => (
                <option key={entryDate} value={entryDate} />
              ))}
            </datalist>
          </label>
          {selectedEntryDate && (
            <button type="button" onClick={() => setSelectedEntryDate("")}>
              Clear Date
            </button>
          )}
        </div>

        {loading ? (
          <p>Loading report...</p>
        ) : columns.length > 0 ? (
          <div style={{ height: 500, width: "100%" }}>
            <DataGrid
              rows={rows}
              columns={dataGridColumns}
              pageSizeOptions={[10, 25, 50]}
              checkboxSelection
              disableSelectionOnClick
              processRowUpdate={processRowUpdate}
              onProcessRowUpdateError={(error) =>
                setMessage(error.message || "Unable to update cell")
              }
            />
          </div>
        ) : (
          <p>No columns available to view.</p>
        )}

        {canAddRows && addableColumns.length > 0 && (
          <section className="add-row-form">
            <h3>Add New Row</h3>
            <form onSubmit={addNewRow}>
              {addableColumns.map((col) => (
                <input
                  key={col.field}
                  type="text"
                  placeholder={col.headerName}
                  value={newRow[col.field] || ""}
                  onChange={(e) =>
                    setNewRow((prev) => ({
                      ...prev,
                      [col.field]: e.target.value,
                    }))
                  }
                />
              ))}
              <button type="submit" disabled={saving.new}>
                {saving.new ? "Adding..." : "Add Row"}
              </button>
            </form>
          </section>
        )}
      </section>
    </main>
  );
}

export default Dashboard;
