
import { useEffect, useState } from 'react'
import './ManagementPages.css'

const initialForm = {
  employee_code: 'EMP001',
  start_date: '',
  end_date: '',
  type: 'leave',
  reason: ''
}

export default function LeavesPage({ onRosterChanged }) {
  const [leaves, setLeaves] = useState([])
  const [employees, setEmployees] = useState([])
  const [form, setForm] = useState(initialForm)
  const [loading, setLoading] = useState(false)
  const [busyId, setBusyId] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [approvalResult, setApprovalResult] = useState(null)

  async function loadData() {
    setLoading(true)
    setError('')

    try {
      const [leaveResponse, employeeResponse] = await Promise.all([
        fetch('/api/leaves'),
        fetch('/api/employees')
      ])

      if (!leaveResponse.ok || !employeeResponse.ok) {
        throw new Error('Unable to load leave or employee records.')
      }

      const leaveData = await leaveResponse.json()
      const employeeData = await employeeResponse.json()

      setLeaves(leaveData.leaves || [])
      setEmployees(employeeData.employees || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  async function submitLeave(event) {
    event.preventDefault()

    setError('')
    setMessage('')
    setApprovalResult(null)

    if (!form.start_date || !form.end_date) {
      setError('Please choose both leave dates.')
      return
    }

    if (form.end_date < form.start_date) {
      setError('End date cannot be before start date.')
      return
    }

    setBusyId('request')

    try {
      const response = await fetch('/api/leaves/request', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(form)
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'Unable to create leave request.'
        )
      }

      setMessage('Leave request submitted. Status: pending.')
      setForm(prev => ({
        ...initialForm,
        employee_code: prev.employee_code
      }))
      await loadData()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId('')
    }
  }

  async function approveLeave(leaveId) {
    setError('')
    setMessage('')
    setApprovalResult(null)
    setBusyId(leaveId)

    try {
      const response = await fetch(
        `/api/leaves/${leaveId}/approve`,
        { method: 'PATCH' }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail || 'Unable to approve leave.'
        )
      }

      setMessage('Leave approved successfully.')
      setApprovalResult(data)

      if (onRosterChanged) {
        onRosterChanged()
      }

      await loadData()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId('')
    }
  }

  const pendingCount = leaves.filter(
    leave => leave.status === 'pending'
  ).length

  const approvedCount = leaves.filter(
    leave => leave.status === 'approved'
  ).length

  return (
    <div className="management-page">
      <div className="management-stats">
        <div>
          <span>Recent Leave Records</span>
          <strong>{leaves.length}</strong>
        </div>
        <div>
          <span>Pending Requests</span>
          <strong>{pendingCount}</strong>
        </div>
        <div>
          <span>Approved Requests</span>
          <strong>{approvedCount}</strong>
        </div>
      </div>

      {error && (
        <div className="management-error" role="alert">
          {error}
        </div>
      )}

      {message && (
        <div className="management-success" role="status">
          {message}
        </div>
      )}

      <section className="management-panel">
        <div className="management-header">
          <div>
            <h2>Request Employee Leave</h2>
            <p>Create a leave request for manager approval.</p>
          </div>
        </div>

        <form className="leave-form" onSubmit={submitLeave}>
          <label>
            Employee
            <select
              value={form.employee_code}
              onChange={e => setForm({
                ...form,
                employee_code: e.target.value
              })}
              required
            >
              <option value="">Select employee</option>
              {employees.filter(e => e.active).map(employee => (
                <option
                  key={employee.employee_code}
                  value={employee.employee_code}
                >
                  {employee.employee_code} — {employee.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Start date
            <input
              type="date"
              value={form.start_date}
              onChange={e => setForm({
                ...form,
                start_date: e.target.value
              })}
              required
            />
          </label>

          <label>
            End date
            <input
              type="date"
              value={form.end_date}
              onChange={e => setForm({
                ...form,
                end_date: e.target.value
              })}
              required
            />
          </label>

          <label>
            Leave type
            <select
              value={form.type}
              onChange={e => setForm({
                ...form,
                type: e.target.value
              })}
            >
              <option value="leave">Leave</option>
              <option value="comp_off">Comp-off</option>
              <option value="unavailable">Unavailable</option>
            </select>
          </label>

          <label className="leave-reason">
            Reason
            <input
              value={form.reason}
              placeholder="Reason for leave..."
              onChange={e => setForm({
                ...form,
                reason: e.target.value
              })}
            />
          </label>

          <button
            type="submit"
            disabled={Boolean(busyId)}
          >
            {busyId === 'request'
              ? 'Submitting...'
              : 'Submit Leave Request'}
          </button>
        </form>
      </section>

      <section className="management-panel">
        <div className="management-header">
          <div>
            <h2>Leave Requests</h2>
            <p>Review recent pending and approved requests.</p>
          </div>

          <button
            className="secondary-button"
            onClick={loadData}
            disabled={loading}
          >
            Refresh
          </button>
        </div>

        {loading && <p>Loading leave records...</p>}

        <div className="management-table-scroll">
          <table className="management-table">
            <thead>
              <tr>
                <th>Employee</th>
                <th>Dates</th>
                <th>Type</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {leaves.map(leave => (
                <tr key={leave.id}>
                  <td>
                    <strong>{leave.employee_name}</strong>
                    <small>{leave.employee_code}</small>
                  </td>

                  <td>
                    {leave.start_date}
                    {leave.start_date !== leave.end_date &&
                      ` to ${leave.end_date}`}
                  </td>

                  <td>{leave.type.replaceAll('_', ' ')}</td>

                  <td>
                    <span className={
                      leave.status === 'approved'
                        ? 'management-tag approved-tag'
                        : leave.status === 'pending'
                        ? 'management-tag pending-tag'
                        : 'management-tag'
                    }>
                      {leave.status}
                    </span>
                  </td>

                  <td>
                    {leave.status === 'pending' ? (
                      <button
                        disabled={Boolean(busyId)}
                        onClick={() => approveLeave(leave.id)}
                      >
                        {busyId === leave.id
                          ? 'Approving...'
                          : 'Approve'}
                      </button>
                    ) : (
                      <span className="management-muted">
                        No action
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!loading && leaves.length === 0 && (
          <p className="management-empty">
            No leave requests found.
          </p>
        )}
      </section>

      {approvalResult && (
        <section className="management-panel">
          <h2>Automatic Roster Revalidation</h2>

          <p>
            Validation status:
            {' '}
            <strong>
              {approvalResult.validation_status}
            </strong>
          </p>

          {(approvalResult.affected_rosters || []).map(
            roster => (
              <div
                className="approval-result"
                key={roster.roster_id}
              >
                <h3>
                  {roster.roster_month} — Version {roster.version}
                </h3>

                <p>
                  Total violations:
                  {' '}
                  <strong>{roster.total_violations}</strong>
                </p>

                {Object.entries(
                  roster.violation_summary || {}
                ).map(([type, count]) => (
                  <p key={type}>
                    {type.replaceAll('_', ' ')}: {count}
                  </p>
                ))}
              </div>
            )
          )}

          {(approvalResult.validation_errors || []).length > 0 && (
            <div className="management-error">
              Some affected rosters could not be validated.
              Check the FastAPI terminal.
            </div>
          )}

          {approvalResult.affected_rosters?.length === 0 && (
            <p>
              No saved roster with this employee's scheduled shifts
              was found for the approved leave dates.
            </p>
          )}
        </section>
      )}
    </div>
  )
}
