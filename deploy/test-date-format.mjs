import assert from 'node:assert/strict'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

if (!process.argv[2]) throw new Error('Usage: node deploy/test-date-format.mjs <compiled-format.js>')
const { formatDate, formatDateTime, daysUntil, formatDays } = await import(
  pathToFileURL(resolve(process.argv[2])).href
)

assert.equal(formatDate('2026-10-08'), '08/10/2026')
assert.equal(formatDate('8/10/2026'), '08/10/2026')
assert.equal(formatDate('2024-02-29'), '29/02/2024')
assert.equal(formatDate('2026-02-29'), '2026-02-29')
assert.equal(formatDate('Restante'), 'Restante')
assert.equal(formatDateTime('Restante'), 'Restante')
assert.equal(formatDateTime('2026-10-08'), '08/10/2026')
assert.equal(formatDate('2026-10-08T03:30:00Z'), '07/10/2026')
assert.equal(formatDateTime('2026-10-08T03:30:00Z'), '07/10/2026, 22:30')
assert.equal(formatDateTime('2026-10-07T22:30:00-05:00'), '07/10/2026, 22:30')
assert.equal(formatDateTime('2026-10-07T22:30:00'), '07/10/2026, 22:30')

// Formatting an already displayed Lima timestamp must not shift it a second time.
for (const instant of ['2026-10-08T03:30:00Z', '2026-10-08T05:00:00Z', '2026-10-08T17:00:00Z']) {
  const localized = new Intl.DateTimeFormat('es-PE', {
    dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Lima',
  }).format(new Date(instant))
  assert.equal(formatDateTime(localized), formatDateTime(instant))
}
assert.equal(formatDateTime('31/2/26, 10:30 p. m.'), '31/2/26, 10:30 p. m.')
assert.equal(formatDateTime('8/10/26, 25:00'), '8/10/26, 25:00')

const beforeLimaMidnight = new Date('2026-10-08T04:59:59Z')
const limaMidnight = new Date('2026-10-08T05:00:00Z')
assert.equal(daysUntil('2026-10-08', beforeLimaMidnight), 1)
assert.equal(daysUntil('2026-10-08', limaMidnight), 0)
assert.equal(daysUntil('7/10/2026', limaMidnight), -1)
assert.equal(daysUntil('2026-10-23', limaMidnight), 15)
assert.equal(daysUntil('2026-10-12', limaMidnight), 4)
assert.equal(daysUntil('2027-01-01', new Date('2026-12-31T17:00:00Z')), 1)
assert.equal(daysUntil('2024-03-01', new Date('2024-02-28T17:00:00Z')), 2)
assert.equal(daysUntil('2026-02-29', limaMidnight), null)
assert.equal(daysUntil('Restante', limaMidnight), null)
assert.equal(formatDays(1), '1 d\u00eda')
assert.equal(formatDays(2), '2 d\u00edas')
assert.equal(formatDays(0), '0 d\u00edas')
console.log(`Date format assertions passed (TZ=${process.env.TZ ?? 'system'}).`)
