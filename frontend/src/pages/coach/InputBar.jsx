import { Send } from "lucide-react";

export default function InputBar({ value, onChange, onSubmit, disabled }) {
  return (
    <form
      onSubmit={(e) => { e.preventDefault(); onSubmit(); }}
      className="border-t border-border p-3 flex gap-2 bg-background"
      data-testid="coach-input-form"
    >
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder="Chiedi al Coach... (es. 'analizza i miei trade di oggi')"
        className="flex-1 px-4 py-2.5 rounded-md bg-secondary border border-border text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/30"
        data-testid="coach-input"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="px-4 py-2.5 rounded-md bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-sm font-medium flex items-center gap-1"
        data-testid="coach-send-btn"
      >
        <Send className="h-4 w-4" />
      </button>
    </form>
  );
}
