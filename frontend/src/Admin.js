import { useCallback, useEffect, useState } from "react";

const API_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";
const emptyForm = {
  username: "",
  password: "",
  role: "User",
  permissions: {},
};

function buildDefaultPermissions(columns, access = "none") {
  return columns.reduce((current, column) => ({
    ...current,
    [column]: access,
  }), {});
}

function Admin({ session, onBack, onLogout }) {
  const [users, setUsers] = useState([]);
  const [columns, setColumns] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [activePanel, setActivePanel] = useState("users");
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [auditLoading, setAuditLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadUsers = useCallback(async function loadUsers() {
    setLoading(true);
    setMessage("");

    try {
      const params = new URLSearchParams({ adminUsername: session.username });
      const response = await fetch(`${API_URL}/admin/users?${params.toString()}`);
      const data = await response.json();

      if (!response.ok || data.error) {
        setMessage(data.error || "Unable to load users");
        return;
      }

      const nextColumns = data.columns || [];
      setColumns(nextColumns);
      setUsers(data.users || data || []);
      setForm((current) => ({
        ...current,
        permissions: {
          ...buildDefaultPermissions(nextColumns),
          ...current.permissions,
        },
      }));
    } catch (error) {
      setMessage("Backend is not reachable. Start the backend on port 8000.");
    } finally {
      setLoading(false);
    }
  }, [session.username]);

  const loadAuditLogs = useCallback(async function loadAuditLogs() {
    setAuditLoading(true);
    setMessage("");

    try {
      const params = new URLSearchParams({
        adminUsername: session.username,
        limit: "1000",
      });
      const response = await fetch(`${API_URL}/admin/audit-logs?${params.toString()}`);
      const data = await response.json();

      if (!response.ok || data.error) {
        setMessage(data.error || data.detail || "Unable to load audit logs");
        return;
      }

      setAuditLogs(data.logs || []);
    } catch (error) {
      setMessage("Backend is not reachable. Start the backend on port 8000.");
    } finally {
      setAuditLoading(false);
    }
  }, [session.username]);

  useEffect(() => {
    loadUsers();
    loadAuditLogs();
  }, [loadUsers, loadAuditLogs]);

  function resetForm() {
    setForm({
      ...emptyForm,
      permissions: buildDefaultPermissions(columns),
    });
    setEditingId("");
  }

  function editUser(user) {
    setEditingId(user.id);
    setForm({
      username: user.username,
      password: "",
      role: user.role || "User",
      permissions: {
        ...buildDefaultPermissions(columns),
        ...(user.permissions || {}),
      },
    });
    setMessage("");
  }

  function setPermission(column, access) {
    setForm((current) => ({
      ...current,
      permissions: {
        ...current.permissions,
        [column]: access,
      },
    }));
  }

  function setAllPermissions(access) {
    setForm((current) => ({
      ...current,
      permissions: buildDefaultPermissions(columns, access),
    }));
  }

  function formatTimestamp(value) {
    if (!value) {
      return "";
    }

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString();
  }

  async function saveUser(event) {
    event.preventDefault();
    setSaving(true);
    setMessage("");

    const body = {
      adminUsername: session.username,
      username: form.username,
      password: form.password,
      role: form.role,
      permissions: form.role === "Admin"
        ? buildDefaultPermissions(columns, "edit")
        : form.permissions,
    };

    try {
      const response = await fetch(
        editingId ? `${API_URL}/admin/users/${editingId}` : `${API_URL}/admin/users`,
        {
          method: editingId ? "PUT" : "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(body),
        }
      );
      const data = await response.json();

      if (!response.ok || data.error) {
        setMessage(data.error || "Unable to save user");
        return;
      }

      setMessage(editingId ? "User updated" : "User added");
      resetForm();
      loadUsers();
    } catch (error) {
      setMessage("Save failed. Check backend connection.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteUser(user) {
    if (!window.confirm(`Delete ${user.username}?`)) {
      return;
    }

    setMessage("");
    try {
      const params = new URLSearchParams({ adminUsername: session.username });
      const response = await fetch(
        `${API_URL}/admin/users/${user.id}?${params.toString()}`,
        { method: "DELETE" }
      );
      const data = await response.json();

      if (!response.ok || data.error) {
        setMessage(data.error || "Unable to delete user");
        return;
      }

      setMessage("User deleted");
      if (editingId === user.id) {
        resetForm();
      }
      loadUsers();
    } catch (error) {
      setMessage("Delete failed. Check backend connection.");
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">LR Portal</p>
          <h1>Admin Users</h1>
        </div>

        <div className="session-actions">
          <span>{session.username}</span>
          <button type="button" onClick={onBack}>Report</button>
          <button
            type="button"
            onClick={() => {
              setActivePanel("users");
              loadUsers();
            }}
          >
            Users
          </button>
          <button
            type="button"
            onClick={() => {
              setActivePanel("logs");
              loadAuditLogs();
            }}
          >
            Logs Report
          </button>
          <button type="button" onClick={onLogout}>Logout</button>
        </div>
      </header>

      {message && (
        <p className={message.includes("failed") || message.includes("Unable") ? "error" : "success"}>
          {message}
        </p>
      )}

      {activePanel === "logs" ? (
        <section className="users-panel audit-panel">
          <div className="add-entry-heading">
            <h2>Logs Report</h2>
            <button type="button" onClick={loadAuditLogs} disabled={auditLoading}>
              {auditLoading ? "Refreshing..." : "Refresh"}
            </button>
          </div>

          {auditLoading ? (
            <div className="empty-state">Loading logs...</div>
          ) : auditLogs.length === 0 ? (
            <div className="empty-state">No logs found.</div>
          ) : (
            <table className="users-table audit-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>LR / Row</th>
                  <th>Column</th>
                  <th>Old Value</th>
                  <th>New Value</th>
                  <th>Updated By</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id}>
                    <td>{formatTimestamp(log.timestamp)}</td>
                    <td>{log.lrNo}</td>
                    <td>{log.columnName}</td>
                    <td>{log.oldValue}</td>
                    <td>{log.newValue}</td>
                    <td>{log.updatedBy}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      ) : (
      <section className="admin-layout">
        <form onSubmit={saveUser} className="admin-form">
          <div className="add-entry-heading">
            <h2>{editingId ? "Edit User" : "Add User"}</h2>
            {editingId && <button type="button" onClick={resetForm}>Cancel</button>}
          </div>

          <label>
            Username
            <input
              value={form.username}
              onChange={(event) => setForm((current) => ({
                ...current,
                username: event.target.value,
              }))}
              required
            />
          </label>

          <label>
            Password
            <input
              value={form.password}
              onChange={(event) => setForm((current) => ({
                ...current,
                password: event.target.value,
              }))}
              placeholder={editingId ? "Leave blank to keep current password" : ""}
              type="password"
              required={!editingId}
            />
          </label>

          <label>
            Role
            <select
              value={form.role}
              onChange={(event) => setForm((current) => ({
                ...current,
                role: event.target.value,
              }))}
            >
              <option value="User">User</option>
              <option value="Admin">Admin</option>
            </select>
          </label>

          <section className="permission-editor">
            <div className="permission-editor-heading">
              <h3>Column Access</h3>
              <div>
                <button type="button" onClick={() => setAllPermissions("none")}>Hide All</button>
                <button type="button" onClick={() => setAllPermissions("view")}>View All</button>
                <button type="button" onClick={() => setAllPermissions("edit")}>Edit All</button>
              </div>
            </div>

            {form.role === "Admin" ? (
              <p className="permission-note">Admin users have edit access to every column.</p>
            ) : columns.length === 0 ? (
              <p className="permission-note">No report columns found yet.</p>
            ) : (
              <div className="permission-grid">
                {columns.map((column) => (
                  <label key={column}>
                    <span>{column}</span>
                    <select
                      value={form.permissions[column] || "none"}
                      onChange={(event) => setPermission(column, event.target.value)}
                    >
                      <option value="none">Hide</option>
                      <option value="view">View</option>
                      <option value="edit">Edit</option>
                    </select>
                  </label>
                ))}
              </div>
            )}
          </section>

          <button type="submit" disabled={saving}>
            {saving ? "Saving..." : editingId ? "Update User" : "Add User"}
          </button>
        </form>

        <section className="users-panel">
          {loading ? (
            <div className="empty-state">Loading users...</div>
          ) : (
            <table className="users-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Role</th>
                  <th>Access</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.username}</td>
                    <td>{user.role}</td>
                    <td>
                      <span className="access-summary">
                        {user.role === "Admin"
                          ? "All edit"
                          : `${Object.values(user.permissions || {}).filter((access) => access === "edit").length} edit, ${Object.values(user.permissions || {}).filter((access) => access === "view").length} view`}
                      </span>
                    </td>
                    <td>
                      <button type="button" onClick={() => editUser(user)}>Edit</button>
                      <button
                        type="button"
                        className="danger-button"
                        onClick={() => deleteUser(user)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </section>
      )}
    </main>
  );
}

export default Admin;
