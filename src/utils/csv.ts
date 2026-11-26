export function escapeCsvField(value: string | number): string {
  const raw = String(value)

  // Spreadsheet apps may treat a cell that starts with =, +, -, @, tab or CR
  // as a formula. Prefix such text with an apostrophe, unless it is a normal
  // number (e.g. -5), so numeric columns stay numeric.
  const text =
    typeof value === 'string' &&
    /^[=+\-@\t\r]/.test(raw) &&
    !Number.isFinite(Number(raw))
      ? `'${raw}`
      : raw

  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

export function toCsv(rows: (string | number)[][]): string {
  return rows.map((row) => row.map(escapeCsvField).join(',')).join('\n')
}
