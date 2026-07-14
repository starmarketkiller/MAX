// Soglia condivisa per le funzioni più pesanti (pavimento riflettente,
// post-processing): sotto questa larghezza si presume un telefono, dove
// certi effetti costano relativamente troppo per il guadagno visivo.
export const isLowEnd = typeof window !== "undefined" && window.innerWidth < 820;
