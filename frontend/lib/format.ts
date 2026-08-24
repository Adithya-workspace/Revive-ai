export function formatCurrency(value: number): string {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(value);
  }
  
  export function formatPercent(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
  }
  
  export function formatDate(iso: string | null): string {
    if (!iso) return "—";
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  }
  
  export function shortId(id: string): string {
    return id.slice(0, 8).toUpperCase();
  }