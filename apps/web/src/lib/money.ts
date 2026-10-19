/** Prices are NGN. The brief shows the symbol as "N" (N300,000.00); change it here to use the naira sign. */
export const NAIRA_SYMBOL = 'N'

const formatter = new Intl.NumberFormat('en-NG', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export function toNumber(value: string | number | null | undefined): number {
  const n = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(n) ? n : 0
}

export function formatNaira(value: string | number | null | undefined): string {
  return `${NAIRA_SYMBOL}${formatter.format(toNumber(value))}`
}

export function hasFee(value: string | number | null | undefined): boolean {
  return toNumber(value) > 0
}
