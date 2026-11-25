import { describe, expect, test } from 'bun:test'

import { escapeCsvField, toCsv } from './csv'

describe('escapeCsvField', () => {
  test('leaves plain values unquoted', () => {
    expect(escapeCsvField('hola')).toBe('hola')
    expect(escapeCsvField(42)).toBe('42')
  })

  test('quotes fields with commas, quotes or line breaks', () => {
    expect(escapeCsvField('a,b')).toBe('"a,b"')
    expect(escapeCsvField('a"b')).toBe('"a""b"')
    expect(escapeCsvField('a\nb')).toBe('"a\nb"')
    expect(escapeCsvField('a\rb')).toBe('"a\rb"')
  })

  test('neutralizes formula injection for string values', () => {
    for (const value of ['=1+1', '+cmd', '-cmd', '@SUM(A1)', '\tfoo', '\rfoo']) {
      const result = escapeCsvField(value)
      const unquoted = result.startsWith('"') ? result.slice(1) : result
      expect(unquoted.startsWith("'")).toBe(true)
    }
  })

  test('keeps genuine numeric values numeric', () => {
    expect(escapeCsvField(-5)).toBe('-5')
    expect(escapeCsvField('-5')).toBe('-5')
    expect(escapeCsvField('+5')).toBe('+5')
  })
})

describe('toCsv', () => {
  test('joins fields and rows', () => {
    expect(toCsv([['a', 1], ['b', 2]])).toBe('a,1\nb,2')
  })

  test('handles empty rows', () => {
    expect(toCsv([[]])).toBe('')
    expect(toCsv([])).toBe('')
  })
})

describe('unavailable-row exports', () => {
  test('credits export emits the 8-column unavailable row', () => {
    const rows = [
      ['Código', 'Cliente', 'Monto original', 'Saldo pendiente', 'Fecha', 'Vencimiento', 'Estado', 'Riesgo'],
      ['No disponible', 'No se pudo cargar la cartera', '', '', '', '', '', ''],
    ]
    const csv = toCsv(rows)
    const lines = csv.split('\n')
    expect(lines).toHaveLength(2)
    expect(lines[1].split(',')).toHaveLength(8)
    expect(lines[1]).toBe('No disponible,No se pudo cargar la cartera,,,,,,')
  })

  test('reports export writes No disponible for portfolio metrics', () => {
    const rows = [
      ['Cartera fiada actual', 'No disponible'],
      ['Monto vencido actual', 'No disponible'],
    ]
    expect(toCsv(rows)).toBe('Cartera fiada actual,No disponible\nMonto vencido actual,No disponible')
  })
})
