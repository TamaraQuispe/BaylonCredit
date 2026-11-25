export function escapeCsvField(value: string | number): string {
  const text = String(value)
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

export function toCsv(rows: (string | number)[][]): string {
  return rows.map((row) => row.map(escapeCsvField).join(',')).join('\n')
}
