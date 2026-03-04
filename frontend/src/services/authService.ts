import { PublicClientApplication } from "@azure/msal-browser";
import type { AuthenticationResult } from "@azure/msal-browser";
import { msalConfig, loginRequest, popupLoginRequest } from "../config/authConfig";
import { getAgentEndpoint, logEnvironmentInfo, envConfig } from "../config/environment";

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  accessToken: string;
  tokenExpiry: Date;
}

class AuthService {
  private msalInstance: PublicClientApplication;
  private currentUser: UserProfile | null = null;

  constructor() {
    this.msalInstance = new PublicClientApplication(msalConfig);
  }

  async initialize(): Promise<void> {
    try {
      // Log environment info for debugging
      logEnvironmentInfo();
      
      await this.msalInstance.initialize();
      await this.handleRedirectPromise();
      this.loadCachedUser();
      
      // Start proactive token refresh checking
      this.startTokenRefreshTimer();
    } catch (error) {
      console.error("Failed to initialize MSAL:", error);
    }
  }

  private startTokenRefreshTimer(): void {
    // Check token status every 60 seconds and refresh if needed
    setInterval(async () => {
      if (this.currentUser && this.isAuthenticated()) {
        try {
          const now = new Date();
          const tokenExpiry = new Date(this.currentUser.tokenExpiry);
          const timeToExpiry = tokenExpiry.getTime() - now.getTime();
          
          // Refresh if token expires in less than 10 minutes
          if (timeToExpiry < 10 * 60 * 1000) {
            console.log("🔄 Proactive token refresh initiated (expires in <10 minutes)");
            await this.refreshToken();
          }
        } catch (error) {
          console.warn("Proactive token refresh failed:", error);
        }
      }
    }, 60 * 1000); // Check every 60 seconds
  }

  private async handleRedirectPromise(): Promise<void> {
    try {
      const response = await this.msalInstance.handleRedirectPromise();
      if (response) {
        await this.handleAuthResult(response);
      }
    } catch (error) {
      console.error("Error handling redirect:", error);
    }
  }

  private loadCachedUser(): void {
    try {
      const cachedUser = localStorage.getItem('hco-microsoft-user');
      if (cachedUser) {
        const user = JSON.parse(cachedUser) as UserProfile;
        
        // Check if token is still valid (with 5 minute buffer)
        const tokenExpiry = new Date(user.tokenExpiry);
        const now = new Date();
        const bufferTime = 5 * 60 * 1000; // 5 minutes in milliseconds
        
        if (tokenExpiry.getTime() > now.getTime() + bufferTime) {
          this.currentUser = user;
        } else {
          localStorage.removeItem('hco-microsoft-user');
          this.currentUser = null;
        }
      }
    } catch (error) {
      console.error("Error loading cached user:", error);
      localStorage.removeItem('hco-microsoft-user');
    }
  }

  async login(): Promise<UserProfile> {
    try {
      console.log('🔑 Starting Microsoft login process...');
      console.log('📋 MSAL Config:', {
        clientId: msalConfig.auth.clientId,
        authority: msalConfig.auth.authority,
        redirectUri: msalConfig.auth.redirectUri,
      });

      // First try silent authentication
      const accounts = this.msalInstance.getAllAccounts();
      console.log(`👥 Found ${accounts.length} cached accounts`);
      
      if (accounts.length > 0) {
        try {
          console.log('🔄 Attempting silent authentication...');
          const response = await this.msalInstance.acquireTokenSilent({
            ...loginRequest,
            account: accounts[0],
          });
          console.log('✅ Silent authentication successful');
          return await this.handleAuthResult(response);
        } catch (silentError) {
          console.log("⚠️ Silent authentication failed, using popup:", silentError);
        }
      }

      // Use different auth flow based on environment
      if (envConfig.isProduction) {
        // Use popup for production (when COOP headers are configured)
        console.log('🌐 Opening Microsoft login popup...');
        const response = await this.msalInstance.acquireTokenPopup(popupLoginRequest);
        console.log('✅ Popup authentication successful');
        return await this.handleAuthResult(response);
      } else {
        // Use redirect for local development to avoid COOP issues
        console.log('🔀 Redirecting to Microsoft login...');
        await this.msalInstance.loginRedirect(loginRequest);
        // The result will be handled by handleRedirectPromise on page load
        throw new Error("Redirect initiated"); // This will be caught and handled
      }
    } catch (error) {
      console.error("❌ Microsoft login failed:", error);
      
      // More specific error messages
      if (error instanceof Error) {
        // Special handling for redirect flow
        if (error.message === "Redirect initiated") {
          // This is expected for local development redirect flow
          console.log("🔀 Login redirect initiated, waiting for return...");
          return new Promise(() => {}); // Return a promise that never resolves since we're redirecting
        }
        
        if (error.message.includes('user_cancelled')) {
          throw new Error("Login was cancelled. Please try again.");
        } else if (error.message.includes('consent_required')) {
          throw new Error("Additional permissions required. Please contact your administrator.");
        } else if (error.message.includes('interaction_required')) {
          throw new Error("Interactive login required. Please try again.");
        }
        throw new Error(`Microsoft login failed: ${error.message}`);
      }
      
      throw new Error("Microsoft login failed. Please check your internet connection and try again.");
    }
  }

  private async handleAuthResult(response: AuthenticationResult): Promise<UserProfile> {
    const account = response.account;
    if (!account) {
      throw new Error("No account information received");
    }

    // Get user profile from Microsoft Graph
    let userProfile: any = {};
    try {
      const graphResponse = await fetch('https://graph.microsoft.com/v1.0/me', {
        headers: {
          'Authorization': `Bearer ${response.accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (graphResponse.ok) {
        userProfile = await graphResponse.json();
      }
    } catch (error) {
      console.warn("Failed to fetch user profile from Graph API:", error);
    }

    const expiryTime = new Date();
    expiryTime.setSeconds(expiryTime.getSeconds() + (response.expiresOn ? 
      Math.floor((response.expiresOn.getTime() - Date.now()) / 1000) : 3600));

    const user: UserProfile = {
      id: account.homeAccountId,
      email: account.username,
      name: userProfile.displayName || account.name || account.username,
      accessToken: response.accessToken,
      tokenExpiry: expiryTime,
    };

    this.currentUser = user;
    localStorage.setItem('hco-microsoft-user', JSON.stringify(user));
    
    // Sync with backend auth_cache.json
    await this.syncWithBackend(user);
    
    return user;
  }

  /**
   * Sync authentication data with backend auth_cache.json
   */
  private async syncWithBackend(user: UserProfile): Promise<void> {
    try {
      const endpoint = getAgentEndpoint('/auth/sync');
      console.log('🔗 Syncing auth with backend:', endpoint);
      
      const payload = {
        access_token: user.accessToken,
        expires_at: user.tokenExpiry.toISOString(),
        client_id: msalConfig.auth.clientId,
        user_email: user.email,
        user_name: user.name,
      };
      
      console.log('📤 Sending auth data:', {
        ...payload,
        access_token: payload.access_token.substring(0, 20) + '...' // Log partial token for debugging
      });

      // Send token to Python agent to update auth_cache.json
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const result = await response.json();
        console.log('✅ Auth synced with backend:', result);
      } else {
        const errorText = await response.text();
        console.warn('⚠️ Backend auth sync failed:', response.status, response.statusText, errorText);
      }
    } catch (error) {
      console.warn('❌ Failed to sync with backend:', error);
      // Don't throw error as this is not critical for frontend functionality
    }
  }

  async getAccessToken(): Promise<string | null> {
    if (!this.currentUser) {
      // If UI state thinks we're logged in but our in-memory user is gone (refresh, tab restore, etc),
      // try to recover from MSAL's account cache silently.
      try {
        const accounts = this.msalInstance.getAllAccounts();
        if (accounts.length > 0) {
          console.log("🔄 No cached user profile, attempting silent token acquisition from MSAL cache...");
          const response = await this.msalInstance.acquireTokenSilent({
            ...loginRequest,
            account: accounts[0],
          });
          await this.handleAuthResult(response);
          // Return the access token directly. TS may still consider `this.currentUser` null inside this block
          // because it doesn't track side-effects of `handleAuthResult`.
          return response.accessToken || null;
        }
      } catch (e) {
        console.warn("⚠️ Silent token recovery failed; user likely needs to login again.", e);
      }

      // Check if backend has valid auth
      const backendAuth = await this.checkBackendAuth();
      if (backendAuth) {
        return backendAuth;
      }
      return null;
    }

    // Check if token needs refresh
    const now = new Date();
    const bufferTime = 5 * 60 * 1000; // 5 minutes
    const tokenExpiry = new Date(this.currentUser.tokenExpiry);

    if (tokenExpiry.getTime() <= now.getTime() + bufferTime) {
      console.log("🔄 Token expiring soon, attempting refresh...");
      try {
        await this.refreshToken();
      } catch (error) {
        console.error("❌ Token refresh failed:", error);
        // Clear expired auth and prompt for re-login
        this.logout();
        throw new Error("Authentication expired. Please log in again.");
      }
    }

    return this.currentUser?.accessToken || null;
  }

  /**
   * Check if backend has valid authentication
   */
  private async checkBackendAuth(): Promise<string | null> {
    try {
      const response = await fetch(getAgentEndpoint('/auth/status'));
      const authStatus = await response.json();
      
      if (authStatus.authenticated && authStatus.expires_at) {
        console.log(`✅ Backend auth valid until: ${authStatus.expires_at}`);
        // If backend has valid auth but frontend doesn't, we might need to re-login
        // to get a fresh token for the frontend
        return null; // Force frontend login to sync
      }
      
      return null;
    } catch (error) {
      console.warn("Failed to check backend auth status:", error);
      return null;
    }
  }

  private async refreshToken(): Promise<void> {
    try {
      const accounts = this.msalInstance.getAllAccounts();
      if (accounts.length === 0) {
        throw new Error("No accounts available for token refresh");
      }

      console.log("🔄 Attempting silent token refresh...");
      const response = await this.msalInstance.acquireTokenSilent({
        ...loginRequest,
        account: accounts[0],
        forceRefresh: true,
      });

      await this.handleAuthResult(response);
      console.log("✅ Token refreshed successfully");
    } catch (error) {
      console.error("❌ Silent token refresh failed:", error);
      
      // Try interactive refresh as fallback
      try {
        console.log("🔄 Attempting interactive token refresh...");
        
        if (envConfig.isProduction) {
          // Use popup for production
          const response = await this.msalInstance.acquireTokenPopup({
            ...popupLoginRequest,
            prompt: "none"
          });
          await this.handleAuthResult(response);
          console.log("✅ Interactive token refresh successful");
        } else {
          // For local development, just force a new login redirect
          console.log("🔀 Forcing login redirect for token refresh...");
          await this.msalInstance.loginRedirect(loginRequest);
          return; // Will be handled on redirect return
        }
      } catch (interactiveError) {
        console.error("❌ Interactive token refresh also failed:", interactiveError);
        this.logout();
        throw new Error("Authentication expired. Please log in again.");
      }
    }
  }

  async logout(): Promise<void> {
    try {
      const accounts = this.msalInstance.getAllAccounts();
      if (accounts.length > 0) {
        if (envConfig.isProduction) {
          // Use popup logout for production
          await this.msalInstance.logoutPopup();
        } else {
          // Use redirect logout for local development
          await this.msalInstance.logoutRedirect({
            postLogoutRedirectUri: envConfig.frontendUrl
          });
          return; // Will redirect away
        }
      }
    } catch (error) {
      console.error("Error during logout:", error);
    }

    this.currentUser = null;
    localStorage.removeItem('hco-microsoft-user');
    localStorage.removeItem('hco-user'); // Remove old auth data too
    
    // Clear backend auth cache too
    this.clearBackendAuth();
  }

  /**
   * Clear backend authentication cache
   */
  private async clearBackendAuth(): Promise<void> {
    try {
      await fetch(getAgentEndpoint('/auth/clear'), { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      console.log("🗑️ Backend auth cache cleared");
    } catch (error) {
      console.warn("Failed to clear backend auth cache:", error);
    }
  }

  getCurrentUser(): UserProfile | null {
    return this.currentUser;
  }

  isAuthenticated(): boolean {
    if (!this.currentUser) {
      return false;
    }

    const now = new Date();
    const tokenExpiry = new Date(this.currentUser.tokenExpiry);
    return tokenExpiry.getTime() > now.getTime();
  }

  async checkAndRefreshToken(): Promise<boolean> {
    if (!this.currentUser) {
      return false;
    }

    try {
      await this.getAccessToken(); // This will refresh if needed
      return this.isAuthenticated();
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const authService = new AuthService();