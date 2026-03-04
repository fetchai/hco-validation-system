export const getApiUrl = (): string => {
  const useProduction = import.meta.env.VITE_USE_PRODUCTION === 'true';
  // Prefer explicit Vite env vars, but fall back to sane defaults so local dev doesn't hard-crash
  // when someone hasn't created a .env.local yet.
  const productionUrl =
    import.meta.env.VITE_PRODUCTION_API_URL ||
    import.meta.env.VITE_PRODUCTION_URL ||
    // Prefer the Vercel rewrite/proxy path in production so we avoid mixed-content/CORS.
    '/api';
  const developmentUrl =
    import.meta.env.VITE_DEVELOPMENT_API_URL ||
    import.meta.env.VITE_DEVELOPMENT_URL ||
    'http://localhost:8096';

  const backendUrlRaw = useProduction ? productionUrl : developmentUrl;
  const backendUrl = String(backendUrlRaw).trim().replace(/\/+$/, '');
  
  // Log the backend URL for debugging
  console.log('Environment:', useProduction ? 'PRODUCTION' : 'DEVELOPMENT');
  console.log('Backend URL:', backendUrl);
  
  return backendUrl;
}