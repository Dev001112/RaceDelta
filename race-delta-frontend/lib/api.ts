const CANDIDATES = [
  typeof window !== 'undefined' && window.__NEXT_DATA__?.env?.NEXT_PUBLIC_API_BASE,
  process.env.NEXT_PUBLIC_API_BASE,
  'http://localhost:3000/api',
  'http://127.0.0.1:3000/api',
  'http://localhost:8000/api',
  'https://api.openf1.org'
].filter(Boolean);

/**
 * fastFetch with timeout
 */
async function fastFetch(url: string, timeout = 700) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  try {
    const res = await fetch(url, { signal: controller.signal });
    clearTimeout(id);
    return res;
  } catch (e) {
    clearTimeout(id);
    throw e;
  }
}

/**
 * probeCandidates - tries candidate base URLs and returns first that responds to /sessions
 * caches result in localStorage for faster subsequent loads
 */
export async function getApiBase() {
  if (typeof window === 'undefined') return CANDIDATES[0] || null;
  const cached = localStorage.getItem('racedelta_api_base');
  if (cached) return cached;
  for (const c of CANDIDATES) {
    try {
      const url = c.replace(/\/+$|\/api$/,'') + '/api/sessions'.replace(/^\//,'/sessions');
      // Try /sessions endpoint directly on base if candidate contains /api already
      const probeUrl = c.endsWith('/api') ? c + '/sessions' : c + '/sessions';
      const res = await fastFetch(probeUrl, 700);
      if (res && res.ok) {
        localStorage.setItem('racedelta_api_base', c);
        return c;
      }
    } catch (e) {
      // ignore and try next
    }
  }
  return null;
}

export const API_BASE = (typeof window !== 'undefined' && localStorage.getItem('racedelta_api_base')) || process.env.NEXT_PUBLIC_API_BASE || null;

/* helper fetchers */
export async function fetcher(url: string) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}
