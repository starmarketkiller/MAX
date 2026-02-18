export function toIso(d: Date | null): string | null {
  return d ? d.toISOString() : null;
}
