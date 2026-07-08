const STORAGE_KEY = "oce_access_password";

/** True when the UI talks to a hosted API (GitHub Pages / ACA), not local compose. */
export const isHostedApi = (): boolean =>
  !(import.meta.env.VITE_API_URL ?? "http://localhost:8000").includes("localhost");

export const getAccessPassword = (): string | null =>
  sessionStorage.getItem(STORAGE_KEY);

export const setAccessPassword = (password: string): void => {
  sessionStorage.setItem(STORAGE_KEY, password);
};

export const clearAccessPassword = (): void => {
  sessionStorage.removeItem(STORAGE_KEY);
};

export const authHeaders = (): Record<string, string> => {
  const password = getAccessPassword();
  if (!password) return {};
  return { Authorization: `Basic ${btoa(`oce:${password}`)}` };
};

/** Append ?access= for routes that cannot send headers (EventSource, PDF tabs). */
export const withAccessQuery = (url: string): string => {
  const password = getAccessPassword();
  if (!password) return url;
  const u = new URL(url);
  u.searchParams.set("access", password);
  return u.toString();
};
