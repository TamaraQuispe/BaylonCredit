import type { ReactNode } from 'react'

export interface Column<T> {
  key: string
  header: string
  align?: 'left' | 'center' | 'right'
  cell: (row: T) => ReactNode
  className?: string
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  rowKey: (row: T) => string
  minWidth?: string
}

const alignClass = {
  left: 'text-left',
  center: 'text-center',
  right: 'text-right',
}

export default function DataTable<T>({
  columns,
  data,
  rowKey,
  minWidth = 'min-w-[700px]',
}: DataTableProps<T>) {
  return (
    <div className="overflow-x-auto">
      <table className={`w-full text-left border-collapse ${minWidth}`}>
        <thead className="bg-surface-container-low border-b border-outline-variant">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={`h-10 px-4 font-table-header text-table-header text-on-surface-variant uppercase whitespace-nowrap ${alignClass[col.align ?? 'left']}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="font-body-md text-body-md text-on-surface divide-y divide-outline-variant">
          {data.map((row) => (
            <tr
              key={rowKey(row)}
              className="h-[56px] hover:bg-surface-container-low transition-colors"
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={`px-4 align-middle ${alignClass[col.align ?? 'left']} ${
                    col.className ?? ''
                  }`}
                >
                  {col.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
