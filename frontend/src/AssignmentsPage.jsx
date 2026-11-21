import { apiFetch } from './lib/api'

import { useEffect, useMemo, useState } from 'react'
import './AssignmentsPage.css'

const API = '/api/assignment-manager'

const today = () => {
  const now = new Date()
  const local = new Date(
    now.getTime() - now.getTimezoneOffset() * 60000
  )
  return local.toISOString().slice(0, 10)
}

function emptyForm() {
  return {
    employee_id: '',
    brand_process_id: '',
    allocation_percent: '100',
    is_primary: true,
    start_date: today(),
    end_date: ''
  }
}

async function requestJson(url, options = {}) {
  const response = await apiFetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    }
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : `Request failed (HTTP ${response.status})`
    )
  }

  return data
}

function AssignmentsPage() {
  const [assignments, setAssignments] = useState([])
  const [employees, setEmployees] = useState([])
  const [brandProcesses, setBrandProcesses] = useState([])

  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [filter, setFilter] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function loadData() {
    setLoading(true)
    setError('')

    try {
      const [items, options] = await Promise.all([
        requestJson(API),
        requestJson(`${API}/options`)
      ])

      setAssignments(items.assignments || [])
      setEmployees(options.employees || [])
      setBrandProcesses(options.brand_processes || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const filtered = useMemo(() => {
    const term = filter.toLowerCase().trim()

    if (!term) return assignments

    return assignments.filter(item =>
      [
        item.employee_name,
        item.employee_code,
        item.pod,
        item.pod_lead,
        item.brand,
        item.process
      ].some(value =>
        String(value || '').toLowerCase().includes(term)
      )
    )
  }, [assignments, filter])

  function updateForm(field, value) {
    setForm(previous => ({
      ...previous,
      [field]: value
    }))
  }

  function resetForm() {
    setForm(emptyForm())
    setEditingId(null)
    setError('')
  }

  function editAssignment(item) {
    setEditingId(item.id)

    setForm({
      employee_id: item.employee_id,
      brand_process_id: item.brand_process_id,
      allocation_percent: String(item.allocation_percent),
      is_primary: Boolean(item.is_primary),
      start_date: item.start_date,
      end_date: item.end_date || ''
    })

    setError('')
    setNotice('')

    document.getElementById(
      'assignment-form'
    )?.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    })
  }

  async function saveAssignment(event) {
    event.preventDefault()

    if (busy) return

    setBusy(true)
    setError('')
    setNotice('')

    const payload = {
      brand_process_id: form.brand_process_id,
      allocation_percent: Number(form.allocation_percent),
      is_primary: form.is_primary,
      start_date: form.start_date,
      end_date: form.end_date || null
    }

    if (!editingId) {
      payload.employee_id = form.employee_id
    }

    try {
      const result = await requestJson(
        editingId ? `${API}/${editingId}` : API,
        {
          method: editingId ? 'PATCH' : 'POST',
          body: JSON.stringify(payload)
        }
      )

      resetForm()
      await loadData()

      setNotice(
        `${result.message}. Revalidate affected rosters before publishing.`
      )
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function endAssignment(item) {
    const proposedDate = window.prompt(
      `End the assignment for ${item.employee_name} â€” ${item.brand} / ${item.process}.\n\nEnter the last valid date (YYYY-MM-DD):`,
      today()
    )

    if (proposedDate === null) return

    if (!/^\d{4}-\d{2}-\d{2}$/.test(proposedDate)) {
      setError('Enter a date in YYYY-MM-DD format.')
      return
    }

    if (!window.confirm(
      'This changes employee eligibility and could affect saved rosters. Continue?'
    )) {
      return
    }

    setBusy(true)
    setError('')
    setNotice('')

    try {
      await requestJson(
        `${API}/${item.id}/end`,
        {
          method: 'POST',
          body: JSON.stringify({
            end_date: proposedDate
          })
        }
      )

      if (editingId === item.id) {
        resetForm()
      }

      await loadData()

      setNotice(
        'Assignment ended. Revalidate affected rosters.'
      )
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const employeeChoices = employees.filter(
    item => item.active
  )

  const processChoices = brandProcesses.filter(
    item => item.active
  )

  const selectedEmployee = employees.find(
    item => item.id === form.employee_id
  )

  const selectedProcess = brandProcesses.find(
    item => item.id === form.brand_process_id
  )

  return (
    <div className="assignment-page">
      <div className="assignment-intro">
        <div>
          <h2>Employee Assignment Management</h2>
          <p>
            Connect employees to brands and processes,
            set allocations, and manage effective dates.
          </p>
        </div>

        <button
          type="button"
          onClick={loadData}
          disabled={loading || busy}
        >
          â†» Refresh Assignments
        </button>
      </div>

      {error && (
        <div className="assignment-error" role="alert">
          âš  {error}
        </div>
      )}

      {notice && (
        <div className="assignment-notice" role="status">
          âœ“ {notice}
        </div>
      )}

      <div className="assignment-warning">
        Assignment changes do not automatically
        regenerate rosters. Run roster validation
        after making changes.
      </div>

      <section
        className="assignment-panel"
        id="assignment-form"
      >
        <h3>
          {editingId
            ? 'Edit Assignment'
            : 'Add New Assignment'}
        </h3>

        <form onSubmit={saveAssignment}>
          <div className="assignment-form-grid">

            <label>
              Employee
              <select
                required
                value={form.employee_id}
                disabled={Boolean(editingId)}
                onChange={event =>
                  updateForm(
                    'employee_id',
                    event.target.value
                  )
                }
              >
                <option value="">
                  Select employee
                </option>

                {employeeChoices.map(item => (
                  <option key={item.id} value={item.id}>
                    {item.employee_code} â€” {item.name}
                  </option>
                ))}

                {editingId &&
                  selectedEmployee &&
                  !selectedEmployee.active && (
                    <option
                      value={selectedEmployee.id}
                    >
                      {selectedEmployee.name} (Inactive)
                    </option>
                  )}
              </select>
            </label>

            <label>
              Brand / Process
              <select
                required
                value={form.brand_process_id}
                onChange={event =>
                  updateForm(
                    'brand_process_id',
                    event.target.value
                  )
                }
              >
                <option value="">
                  Select brand and process
                </option>

                {processChoices.map(item => (
                  <option key={item.id} value={item.id}>
                    {item.brand} â€” {item.process}
                  </option>
                ))}

                {selectedProcess &&
                  !selectedProcess.active && (
                    <option value={selectedProcess.id}>
                      {selectedProcess.brand} â€”
                      {selectedProcess.process} (Inactive)
                    </option>
                  )}
              </select>
            </label>

            <label>
              Allocation (%)
              <input
                type="number"
                min="1"
                max="100"
                step="0.1"
                required
                value={form.allocation_percent}
                onChange={event =>
                  updateForm(
                    'allocation_percent',
                    event.target.value
                  )
                }
              />
            </label>

            <label>
              Start Date
              <input
                type="date"
                required
                value={form.start_date}
                onChange={event =>
                  updateForm(
                    'start_date',
                    event.target.value
                  )
                }
              />
            </label>

            <label>
              End Date (optional)
              <input
                type="date"
                value={form.end_date}
                onChange={event =>
                  updateForm(
                    'end_date',
                    event.target.value
                  )
                }
              />
            </label>

            <label className="assignment-check">
              <input
                type="checkbox"
                checked={form.is_primary}
                onChange={event =>
                  updateForm(
                    'is_primary',
                    event.target.checked
                  )
                }
              />
              Primary assignment
            </label>
          </div>

          {selectedEmployee && (
            <p className="assignment-context">
              Pod: <strong>{selectedEmployee.pod}</strong>
              {' Â· '}
              Pod lead:
              <strong> {selectedEmployee.pod_lead}</strong>
            </p>
          )}

          <div className="assignment-actions">
            <button
              type="submit"
              className="assignment-primary"
              disabled={busy}
            >
              {busy
                ? 'Saving...'
                : editingId
                ? 'Save Changes'
                : 'Create Assignment'}
            </button>

            <button
              type="button"
              onClick={resetForm}
              disabled={busy}
            >
              Clear Form
            </button>
          </div>
        </form>
      </section>

      <section className="assignment-panel">
        <div className="assignment-list-header">
          <div>
            <h3>Existing Assignments</h3>
            <p>
              {filtered.length} of {assignments.length}
              {' '}assignments shown
            </p>
          </div>

          <input
            type="search"
            placeholder="Search employee, brand, process, pod..."
            value={filter}
            onChange={event =>
              setFilter(event.target.value)
            }
          />
        </div>

        <div className="assignment-table-scroll">
          <table className="assignment-table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Pod / Lead</th>
                <th>Brand / Process</th>
                <th>Allocation</th>
                <th>Dates</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {filtered.map(item => (
                <tr key={item.id}>
                  <td>
                    <strong>{item.employee_name}</strong>
                    <small>{item.employee_code}</small>
                  </td>

                  <td>
                    {item.pod}
                    <small>Lead: {item.pod_lead}</small>
                  </td>

                  <td>
                    <strong>{item.brand}</strong>
                    <small>{item.process}</small>

                    {item.is_primary && (
                      <span className="assignment-primary-tag">
                        Primary
                      </span>
                    )}
                  </td>

                  <td>
                    {item.allocation_percent}%
                  </td>

                  <td>
                    {item.start_date}
                    <small>
                      To: {item.end_date || 'Ongoing'}
                    </small>
                  </td>

                  <td>
                    <div className="assignment-row-actions">
                      <button
                        type="button"
                        onClick={() => editAssignment(item)}
                        disabled={busy}
                      >
                        Edit
                      </button>

                      <button
                        type="button"
                        className="assignment-end-btn"
                        onClick={() => endAssignment(item)}
                        disabled={busy}
                      >
                        End
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {!loading && filtered.length === 0 && (
            <p className="assignment-empty">
              No assignments match your search.
            </p>
          )}

          {loading && (
            <p className="assignment-empty">
              Loading assignments...
            </p>
          )}
        </div>
      </section>
    </div>
  )
}

export default AssignmentsPage

