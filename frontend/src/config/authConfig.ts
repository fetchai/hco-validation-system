import type { Configuration, PopupRequest, RedirectRequest } from "@azure/msal-browser";
import { envConfig } from "./environment";

const runtimeRedirectUri =
  typeof window !== "undefined" && window.location
    ? window.location.origin
    : envConfig.frontendUrl;

// MSAL configuration with environment-specific settings
export const msalConfig: Configuration = {
  auth: {
    clientId: envConfig.microsoftClientId,
    authority: "https://login.microsoftonline.com/common",
    // Always redirect back to the current domain (prevents surprise redirects to another site
    // due to mis-set env vars or stale config).
    redirectUri: runtimeRedirectUri,
    postLogoutRedirectUri: runtimeRedirectUri,
  },
  cache: {
    cacheLocation: "localStorage",
    storeAuthStateInCookie: envConfig.isProduction, // Use cookies in production for better persistence
  },
  system: {
    windowHashTimeout: 60000,
    iframeHashTimeout: 6000,
    loadFrameTimeout: 0,
    navigateFrameWait: 0,
    // Additional settings for local development
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (containsPii) {
          return;
        }
        console.log(`[MSAL] ${level}: ${message}`);
      },
      piiLoggingEnabled: false,
    }
  },
};

// Scopes for API access - Use redirect request for local development
export const loginRequest: RedirectRequest = {
  scopes: [
    // Delegated scopes suitable for personal Microsoft accounts
    "https://graph.microsoft.com/Files.ReadWrite",
    "https://graph.microsoft.com/User.Read",
    "openid",
    "profile",
    "email"
  ],
  prompt: "select_account",
};

// Popup request for production (when COOP headers are properly configured)
export const popupLoginRequest: PopupRequest = {
  scopes: [
    // Delegated scopes suitable for personal Microsoft accounts
    "https://graph.microsoft.com/Files.ReadWrite",
    "https://graph.microsoft.com/User.Read",
    "openid",
    "profile",
    "email"
  ],
  prompt: "select_account",
};

export const graphConfig = {
  graphMeEndpoint: "https://graph.microsoft.com/v1.0/me",
};