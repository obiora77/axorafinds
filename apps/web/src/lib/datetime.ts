/** Short, locale-stable labels for the staff dashboard. */
const dateFormatter = new Intl.DateTimeFormat('en-NG', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

const dateTimeFormatter = new Intl.DateTimeFormat('en-NG', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

function toDate(value: string | null | undefined): Date | null {
  if (!value) return null
  // A date-only value (preferred inspection date) is parsed as UTC midnight by
  // `new Date`, which can display as the previous day west of Greenwich. Build it
  // as a local date at noon instead so the calendar day never shifts.
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  const date = dateOnly
    ? new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3]), 12)
    : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDate(value: string | null | undefined): string {
  const date = toDate(value)
  return date ? dateFormatter.format(date) : '—'
}

export function formatDateTime(value: string | null | undefined): string {
  const date = toDate(value)
  return date ? dateTimeFormatter.format(date) : '—'
}
