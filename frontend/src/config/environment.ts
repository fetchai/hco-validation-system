// Environment configuration using your existing .env.local setup

export interface EnvironmentConfig {
  isProduction: boolean;
  frontendUrl: string;
  agentUrl: string;
  microsoftClientId: string;
}

export const getEnvironmentConfig = (): EnvironmentConfig => {
  // Detect environment based on various factors
  const isDev = import.meta.env.DEV; // Vite's built-in development flag
  const useProductionFlag = import.meta.env.VITE_USE_PRODUCTION === 'true';
  const isLocalhostOrDev = window.location.hostname === 'localhost' || 
                           window.location.hostname === '127.0.0.1' ||
                           window.location.port === '5173' ||
                           window.location.port === '5174';
  // Treat any non-localhost hosted build as production-capable (custom domains, Vercel, etc).
  // You can still force behavior via VITE_USE_PRODUCTION.
  const isHosted = !isLocalhostOrDev;
  
  // Force local development if we're running on localhost.
  // Otherwise, production is enabled when either the flag is set, or we're running a built (non-dev) hosted site.
  const isProduction = !isDev && (useProductionFlag || isHosted);
  
  // Determine the correct frontend URL based on current location for local dev
  let frontendUrl: string;
  // Use explicit config if provided; otherwise use the current origin.
  // NOTE: For Microsoft login to work, this URL (or its full redirect URI) must be added to Azure App Registration Redirect URIs.
  frontendUrl = (import.meta.env.VITE_FRONTEND_URL || window.location.origin).trim().replace(/\/+$/, '');
  
  return {
    isProduction,
    frontendUrl,
    agentUrl: String(
      isProduction
        // Default to Vercel rewrite/proxy to avoid mixed-content/CORS.
        ? import.meta.env.VITE_PRODUCTION_API_URL || '/api'
        : import.meta.env.VITE_DEVELOPMENT_API_URL || 'http://localhost:8096'
    )
      .trim()
      .replace(/\/+$/, ''),
    microsoftClientId: import.meta.env.VITE_MICROSOFT_CLIENT_ID || '0a32d1c8-d666-4aa0-aaf9-da6a591343c5'
  };
};

// Export dynamic config getter (not singleton since it depends on window.location)
export const envConfig = {
  get isProduction() { return getEnvironmentConfig().isProduction; },
  get frontendUrl() { return getEnvironmentConfig().frontendUrl; },
  get agentUrl() { return getEnvironmentConfig().agentUrl; },
  get microsoftClientId() { return getEnvironmentConfig().microsoftClientId; },
};

// Helper function to get agent endpoint URL
export const getAgentEndpoint = (path: string): string => {
  const config = getEnvironmentConfig();
  return `${config.agentUrl}${path}`;
};

// Helper function to log environment info
export const logEnvironmentInfo = (): void => {
  const config = getEnvironmentConfig();
  console.log('🌍 Environment Configuration:', {
    environment: config.isProduction ? 'PRODUCTION' : 'DEVELOPMENT',
    frontendUrl: config.frontendUrl,
    agentUrl: config.agentUrl,
    hostname: window.location.hostname,
    port: window.location.port,
    origin: window.location.origin,
    isDev: import.meta.env.DEV,
    useProductionFlag: import.meta.env.VITE_USE_PRODUCTION,
    isProduction: config.isProduction,
  });
};