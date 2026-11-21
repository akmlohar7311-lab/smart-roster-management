
import CreateShiftForm from './CreateShiftForm'
import { useEffect, useMemo, useState } from 'react'
import './RosterEditorPage.css'

const PAGE_SIZE = 20

async function apiRequest(url, options = {}) {
  const response = await fetch(url, options)
  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const detail = data.detail

    throw new Error(
      typeof detail === 'string'
        ? detail
        : `Request failed (HTTP ${response.status})`
    )
  }

  return data
}

function timeLabel(value) {
  return String(value || '').slice(0, 5)
}

export default function RosterEditorPage() {
  const [month, setMonth] = useState('2026-12')
  const [roster, setRoster] = useState(null)
  const [selectedId, setSelectedId] = useState('')
  const [employeeFilter, setEmployeeFilter] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)

  const [backups, setBackups] = useState(null)
  const [replacementCode, setReplacementCode] = useState('')
  const [validation, setValidation] = useState(null)

  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const entries = roster?.entries || []

  const selected = entries.find(
    entry => entry.entry_id === selectedId
  )

  async function loadRoster(preferredEntryId = '') {
    setLoading(true)
    setError('')

    try {
      const [year, monthNumber] = month.split('-')

      const data = await apiRequest(
        `/api/roster-view/monthly?year=${year}&month=${Number(monthNumber)}`
      )

      setRoster(data)

      setSelectedId(previous => {
        const wanted = preferredEntryId || previous

        return data.entries.some(e => e.entry_id === wanted)
          ? wanted
          : ''
      })

      return data
    } catch (err) {
      setError(err.message)
      setRoster(null)
      setSelectedId('')
      return null
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setRoster(null)
    setSelectedId('')
    setBackups(null)
    setValidation(null)
    setReplacementCode('')
    setPage(1)
    loadRoster()
  }, [month])

  const filtered = useMemo(() => {
    return entries.filter(entry => {
      if (
        employeeFilter &&
        entry.employee_code !== employeeFilter
      ) return false

      if (
        dateFilter &&
        entry.work_date !== dateFilter
      ) return false

      if (
        statusFilter &&
        entry.status !== statusFilter
      ) return false

      return true
    })
  }, [entries, employeeFilter, dateFilter, statusFilter])

  const employeeOptions = useMemo(() => {
    const unique = new Map()

    entries.forEach(entry => {
      unique.set(
        entry.employee_code,
        `${entry.employee_code} — ${entry.employee_name}`
      )
    })

    return [...unique.entries()].sort(
      (a, b) => a[0].localeCompare(b[0])
    )
  }, [entries])

  const pageCount = Math.max(
    1,
    Math.ceil(filtered.length / PAGE_SIZE)
  )

  const visibleEntries = filtered.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE
  )

  function selectShift(entry) {
    setSelectedId(entry.entry_id)
    setBackups(null)
    setReplacementCode('')
    setError('')
    setMessage('')
  }

  async function findBackups() {
    if (!selected) return

    setBusy(true)
    setError('')
    setBackups(null)

    try {
      const data = await apiRequest(
        `/api/backups/available/${selected.entry_id}`
      )

      setBackups(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function validateCurrentRoster() {
    if (!roster) return

    setBusy(true)
    setError('')

    try {
      const data = await apiRequest(
        `/api/rosters/${roster.roster_id}/validate`
      )

      setValidation(data)
      return data
    } catch (err) {
      setError(err.message)
      return null
    } finally {
      setBusy(false)
    }
  }

  async function cancelShift() {
    if (!selected || selected.status !== 'working') return

    const confirmed = window.confirm(
      `Cancel ${selected.employee_name}'s shift on ` +
      `${selected.work_date}, ${timeLabel(selected.start_time)}` +
      `–${timeLabel(selected.end_time)}?`
    )

    if (!confirmed) return

    const entryId = selected.entry_id

    setBusy(true)
    setError('')
    setMessage('')

    try {
      await apiRequest(
        `/api/roster-editor/entries/${entryId}/cancel`,
        { method: 'PATCH' }
      )

      setMessage('Shift cancelled successfully.')
      setBackups(null)
      setValidation(null)

      await loadRoster(entryId)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function reassignShift() {
    if (!selected) return

    const code = replacementCode.trim().toUpperCase()

    if (!code) {
      setError('Please select or enter an employee code.')
      return
    }

    const action = selected.status === 'cancelled'
      ? 'fill'
      : 'replace'

    const confirmed = window.confirm(
      `${action === 'fill' ? 'Fill' : 'Replace'} this shift ` +
      `using ${code}?`
    )

    if (!confirmed) return

    setBusy(true)
    setError('')
    setMessage('')

    try {
      const result = await apiRequest(
        `/api/roster-editor/entries/${selected.entry_id}/${action}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ employee_code: code })
        }
      )

      setMessage(
        result.message || 'Roster edit completed.'
      )

      setBackups(null)
      setReplacementCode('')
      setValidation(null)

      const refreshed = await loadRoster(
        result.new_entry_id || ''
      )

      if (refreshed) {
        try {
          const latest = await apiRequest(
            `/api/rosters/${refreshed.roster_id}/validate`
          )

          setValidation(latest)
        } catch (validationError) {
          setError(
            'Shift was updated, but revalidation failed: ' +
            validationError.message
          )
        }
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  function resetFilters() {
    setEmployeeFilter('')
    setDateFilter('')
    setStatusFilter('')
    setPage(1)
  }

  return (
    <div className="editor-page">
      <section className="editor-panel">
        <div className="editor-header">
          <div>
            <h2>Manual Roster Editor</h2>
            <p>
              Select a shift, find backups, and make
              validated roster changes.
            </p>
          </div>

          <div className="editor-header-actions">
            <input
              type="month"
              aria-label="Roster month"
              value={month}
              onChange={e => setMonth(e.target.value)}
            />

            <button
              onClick={() => loadRoster()}
              disabled={loading || busy}
            >
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="editor-error" role="alert">
            {error}
          </div>
        )}

        {message && (
          <div className="editor-success" role="status">
            {message}
          </div>
        )}

        {loading && <p>Loading roster...</p>}

        {roster && (
          <div className="editor-stats">
            <div>
              <span>Roster Version</span>
              <strong>V{roster.version}</strong>
            </div>

            <div>
              <span>Working Shifts</span>
              <strong>{roster.working_shifts}</strong>
            </div>

            <div>
              <span>Cancelled Shifts</span>
              <strong>{roster.cancelled_shifts}</strong>
            </div>

            <div>
              <span>Roster Status</span>
              <strong>{roster.status}</strong>
            </div>
          </div>
        )}
      </section>

      {roster && (
        <>
          <section className="editor-panel">
            <h3>1. Find a shift</h3>

            <div className="editor-filters">
              <label>
                Employee
                <select
                  value={employeeFilter}
                  onChange={e => {
                    setEmployeeFilter(e.target.value)
                    setPage(1)
                  }}
                >
                  <option value="">All employees</option>

                  {employeeOptions.map(([code, name]) => (
                    <option key={code} value={code}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Date
                <input
                  type="date"
                  value={dateFilter}
                  onChange={e => {
                    setDateFilter(e.target.value)
                    setPage(1)
                  }}
                />
              </label>

              <label>
                Status
                <select
                  value={statusFilter}
                  onChange={e => {
                    setStatusFilter(e.target.value)
                    setPage(1)
                  }}
                >
                  <option value="">All statuses</option>
                  <option value="working">Working</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </label>

              <button
                className="editor-secondary"
                onClick={resetFilters}
              >
                Clear
              </button>
            </div>

            <p className="editor-muted">
              {filtered.length} matching shifts.
              Select one using the button in the last column.
            </p>

            <div className="editor-table-scroll">
              <table className="editor-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Employee</th>
                    <th>Brand</th>
                    <th>Process</th>
                    <th>Time</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>

                <tbody>
                  {visibleEntries.map(entry => (
                    <tr
                      key={entry.entry_id}
                      className={
                        selectedId === entry.entry_id
                          ? 'editor-selected-row'
                          : ''
                      }
                    >
                      <td>{entry.work_date}</td>

                      <td>
                        <strong>{entry.employee_name}</strong>
                        <small>{entry.employee_code}</small>
                      </td>

                      <td>{entry.brand}</td>
                      <td>{entry.process_code}</td>

                      <td>
                        {timeLabel(entry.start_time)}
                        {'–'}
                        {timeLabel(entry.end_time)}
                      </td>

                      <td>
                        <span className={
                          entry.status === 'working'
                            ? 'editor-badge working'
                            : 'editor-badge cancelled'
                        }>
                          {entry.status}
                        </span>
                      </td>

                      <td>
                        <button
                          className="editor-secondary"
                          onClick={() => selectShift(entry)}
                        >
                          Select
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="editor-pagination">
              <span>Page {page} of {pageCount}</span>

              <div>
                <button
                  className="editor-secondary"
                  disabled={page <= 1}
                  onClick={() => setPage(p => p - 1)}
                >
                  Previous
                </button>

                <button
                  className="editor-secondary"
                  disabled={page >= pageCount}
                  onClick={() => setPage(p => p + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          </section>

          {selected && (
            <section className="editor-panel">
              <h3>2. Edit the selected shift</h3>

              <div className="editor-selected-details">
                <div>
                  <span>Employee</span>
                  <strong>
                    {selected.employee_name}
                    {' '}({selected.employee_code})
                  </strong>
                </div>

                <div>
                  <span>Brand / Process</span>
                  <strong>
                    {selected.brand} / {selected.process_code}
                  </strong>
                </div>

                <div>
                  <span>Date</span>
                  <strong>{selected.work_date}</strong>
                </div>

                <div>
                  <span>Time</span>
                  <strong>
                    {timeLabel(selected.start_time)}
                    {' – '}
                    {timeLabel(selected.end_time)}
                  </strong>
                </div>

                <div>
                  <span>Status</span>
                  <strong>{selected.status}</strong>
                </div>
              </div>

              <div className="editor-action-row">
                <button
                  className="editor-danger-button"
                  onClick={cancelShift}
                  disabled={
                    busy ||
                    roster.status !== 'draft' ||
                    selected.status !== 'working'
                  }
                >
                  Cancel Shift
                </button>

                <button
                  onClick={findBackups}
                  disabled={busy || roster.status !== 'draft'}
                >
                  Find Available Backups
                </button>
              </div>

              {backups && (
                <div className="editor-backups">
                  <h3>Available backup candidates</h3>

                  <p className="editor-muted">
                    Already assigned:
                    {' '}{backups.assigned_backups.length}
                    {' '}· Potential temporary assignments:
                    {' '}{backups.potential_backups.length}
                  </p>

                  {backups.assigned_backups.map(employee => (
                    <button
                      key={employee.employee_code}
                      className="editor-candidate"
                      onClick={() => setReplacementCode(
                        employee.employee_code
                      )}
                    >
                      <strong>
                        {employee.employee_code} — {employee.name}
                      </strong>
                      <span>Already assigned · Select</span>
                    </button>
                  ))}

                  {backups.potential_backups.map(employee => (
                    <div
                      className="editor-potential"
                      key={employee.employee_code}
                    >
                      <strong>
                        {employee.employee_code} — {employee.name}
                      </strong>

                      <span>
                        Requires a separate temporary assignment
                      </span>
                    </div>
                  ))}

                  {backups.assigned_backups.length === 0 &&
                    backups.potential_backups.length === 0 && (
                      <p className="editor-muted">
                        No backup candidates found under
                        the current scheduling rules.
                      </p>
                    )}
                </div>
              )}

              <div className="editor-reassignment">
                <label>
                  Replacement employee code
                  <input
                    value={replacementCode}
                    placeholder="Example: EMP031"
                    onChange={e => setReplacementCode(
                      e.target.value.toUpperCase()
                    )}
                  />
                </label>

                <button
                  onClick={reassignShift}
                  disabled={
                    busy ||
                    roster.status !== 'draft' ||
                    !replacementCode.trim()
                  }
                >
                  {selected.status === 'cancelled'
                    ? 'Fill Cancelled Shift'
                    : 'Replace Working Shift'}
                </button>
              </div>

              <p className="editor-muted">
                Every replacement is checked by FastAPI for
                valid assignment, approved leave, fixed weekly
                offs, overlapping shifts and daily capacity.
              </p>
            </section>
          )}

          <CreateShiftForm
            rosterId={roster.roster_id}
            month={month}
            onCreated={async (entryId) => {
              setBackups(null)
              setValidation(null)
              setEmployeeFilter('')
              setDateFilter('')
              setStatusFilter('')
              setPage(1)

              const updated = await loadRoster(entryId)

              if (updated) {
                setMessage('Missing shift created successfully.')
              }
            }}
          />

          <section className="editor-panel">
            <div className="editor-header">
              <div>
                <h3>4. Validate the roster</h3>
                <p>
                  Check the current roster against
                  employee availability and staffing rules.
                </p>
              </div>

              <button
                onClick={validateCurrentRoster}
                disabled={busy}
              >
                Run Validation
              </button>
            </div>

            {validation && (
              <div className="editor-validation">
                <div>
                  <span>Saved entries</span>
                  <strong>{validation.total_shifts}</strong>
                </div>

                <div>
                  <span>Total violations</span>
                  <strong>{validation.total_violations}</strong>
                </div>

                <div className="editor-validation-types">
                  {Object.entries(
                    validation.violation_summary || {}
                  ).map(([type, count]) => (
                    <p key={type}>
                      {type.replaceAll('_', ' ')}: {count}
                    </p>
                  ))}
                </div>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
