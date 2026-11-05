// Dark (default) or light, remembered per browser; storage failures never break theming.
const KEY = 'omnisight.theme'
const ls = () => { try { return globalThis.localStorage } catch { return null } }

export function readTheme(storage = ls()) {
  try {
    const t = storage?.getItem(KEY)
    return t === 'light' || t === 'dark' ? t : 'dark'
  } catch {
    return 'dark'
  }
}

export function writeTheme(theme, storage = ls()) {
  try { storage?.setItem(KEY, theme); return true } catch { return false }
}

export function applyTheme(theme) { document.documentElement.dataset.theme = theme }
