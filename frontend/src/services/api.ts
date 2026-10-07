export const BASE_URL = import.meta.env.VITE_API_URL || '';
export const API_URL = BASE_URL ? `${BASE_URL}/api` : '/api';

export function getApiUrl(path: string): string {
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    if (cleanPath.startsWith('/api/')) {
        return BASE_URL ? `${BASE_URL}${cleanPath}` : cleanPath;
    }
    return `${API_URL}${cleanPath}`;
}

import type { ScreenerResponse, ScreenerScope, WatchlistResponse, ScreenerPreset } from '../types';

export async function fetchScreenerData(scope: ScreenerScope = 'all', refresh = false): Promise<ScreenerResponse> {
    const res = await fetch(getApiUrl(`/screener?scope=${scope}&refresh=${refresh}`));
    if (!res.ok) {
        throw new Error(`Error ${res.status}: Fallo al cargar datos del screener`);
    }
    return res.json();
}

export async function fetchWatchlistData(): Promise<WatchlistResponse> {
    const res = await fetch(getApiUrl('/watchlist'));
    if (!res.ok) {
        throw new Error(`Error ${res.status}: Fallo al cargar watchlist`);
    }
    return res.json();
}

export async function addTickerToWatchlist(ticker: string, notes?: string): Promise<void> {
    const url = getApiUrl(`/watchlist/${encodeURIComponent(ticker)}${notes ? `?notes=${encodeURIComponent(notes)}` : ''}`);
    const res = await fetch(url, { method: 'POST' });
    if (!res.ok) {
        throw new Error(`Error ${res.status}: Fallo al agregar ticker a watchlist`);
    }
}

export async function removeTickerFromWatchlist(ticker: string): Promise<void> {
    const url = getApiUrl(`/watchlist/${encodeURIComponent(ticker)}`);
    const res = await fetch(url, { method: 'DELETE' });
    if (!res.ok) {
        throw new Error(`Error ${res.status}: Fallo al eliminar ticker de watchlist`);
    }
}

export async function fetchScreenerPresets(): Promise<{ presets: ScreenerPreset[] }> {
    const res = await fetch(getApiUrl('/screener/presets'));
    if (!res.ok) {
        throw new Error(`Error ${res.status}: Fallo al cargar presets del screener`);
    }
    return res.json();
}
