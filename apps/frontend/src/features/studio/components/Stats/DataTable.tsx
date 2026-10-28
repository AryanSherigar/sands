import React from "react";
import type { DataTableProps } from "./DataTable.types";

const HEADER_CELL =
  "border-b border-border-subtle px-3 py-2 text-left font-medium text-content-muted";
const BODY_CELL =
  "border-b border-border-subtle px-3 py-2 font-mono tabular-nums text-content";

export const DataTable: React.FC<DataTableProps> = ({ table, caption }) => (
  <div className="overflow-x-auto">
    <table className="w-full border-collapse font-sans text-sm">
      <caption className="sr-only">{caption}</caption>
      <thead>
        <tr>
          {table.columns.map((column) => (
            <th key={column} scope="col" className={HEADER_CELL}>
              {column}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {table.rows.map((row, rowIndex) => (
          <tr key={`${rowIndex}-${row[0]}`}>
            {row.map((cell, cellIndex) => (
              <td key={table.columns[cellIndex]} className={BODY_CELL}>
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);
