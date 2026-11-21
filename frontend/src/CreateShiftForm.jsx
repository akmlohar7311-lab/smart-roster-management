
import { useState } from 'react'

const PROCESSES = [
  {
    label: 'FitFuel — Abandoned Cart Conversions',
    id: '3e0c11f3-f5cb-4a93-8503-4a47b6be8126'
  },
  {
    label: 'FitFuel — Customer Support',
    id: '5953a851-86cd-4a83-8455-96bdc3f20db7'
  },
  {
    label: 'GlowNest — Abandoned Cart Conversions',
    id: '4e427d96-1a80-4008-b9bf-739dc32d7692'
  },
  {
    label: 'GlowNest — Customer Support',
    id: 'c5dd0181-f56b-46ff-a76a-e712123980a4'
  }
]

export default function CreateShiftForm({
  rosterId,
  month,
  onCreated
}) {
  const [employeeCode, setEmployeeCode] = useState('')
  const [processId, setProcessId] = useState('')
  const [workDate, setWorkDate] = useState('')
  const [startTime, setStartTime] = useState('10:00')
  const [endTime, setEndTime] = useState('14:00')

  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()

    setError('')
    setMessage('')

    if (!rosterId) {
      setError('Load a roster first.')
      return
    }

    if (!workDate || workDate.slice(0, 7) !== month) {
      setError('Shift date must belong to the selected roster month.')
      return
    }

    if (endTime <= startTime) {
      setError('End time must be after start time.')
      return
    }

    setBusy(true)

    try {
      const response = await fetch(
        `/api/roster-editor/rosters/${rosterId}/shifts`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            employee_code: employeeCode.trim().toUpperCase(),
            brand_process_id: processId,
            work_date: workDate,
            start_time: `${startTime}:00`,
            end_time: `${endTime}:00`
          })
        }
      )

      const data = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : `Request failed (HTTP ${response.status})`
        )
      }

      setMessage('Shift created successfully.')
      setEmployeeCode('')

      if (onCreated) {
        await onCreated(data.entry_id)
      }
    } catch (err) {
      setError(err.message || 'Could not create shift.')
    } finally {
      setBusy(false)
    }
  }

  const year = Number(month.slice(0, 4))
  const monthNumber = Number(month.slice(5, 7))

  const lastDay = new Date(
    year,
    monthNumber,
    0
  ).getDate()

  return (
    <section className="editor-panel create-shift-panel">
      <h3>3. Create Missing Shift</h3>

      <p className="editor-muted">
        Fill a coverage gap. The backend checks assignments,
        approved leave, daily limits, overlapping shifts,
        and process operating hours.
      </p>

      <form onSubmit={handleSubmit}>
        <label>
          Employee Code

          <input
            value={employeeCode}
            onChange={e => setEmployeeCode(e.target.value)}
            placeholder="EMP031"
            required
          />
        </label>

        <label>
          Brand and Process

          <select
            value={processId}
            onChange={e => setProcessId(e.target.value)}
            required
          >
            <option value="">Select process</option>

            {PROCESSES.map(process => (
              <option
                key={process.id}
                value={process.id}
              >
                {process.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          Work Date

          <input
            type="date"
            value={workDate}
            min={`${month}-01`}
            max={`${month}-${String(lastDay).padStart(2, '0')}`}
            onChange={e => setWorkDate(e.target.value)}
            required
          />
        </label>

        <label>
          Start Time

          <input
            type="time"
            value={startTime}
            onChange={e => setStartTime(e.target.value)}
            required
          />
        </label>

        <label>
          End Time

          <input
            type="time"
            value={endTime}
            onChange={e => setEndTime(e.target.value)}
            required
          />
        </label>

        <button
          type="submit"
          disabled={busy || !rosterId}
        >
          {busy ? 'Creating...' : 'Create Shift'}
        </button>
      </form>

      {message && (
        <p className="create-shift-success" role="status">
          {message}
        </p>
      )}

      {error && (
        <p className="create-shift-error" role="alert">
          {error}
        </p>
      )}
    </section>
  )
}
