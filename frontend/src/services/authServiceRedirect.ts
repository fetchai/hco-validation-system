import { PublicClientApplication } from "@azure/msal-browser";
import type { AuthenticationResult } from "@azure/msal-browser";
import { msalConfig, loginRequest } from "../config/authConfig";
import { getAgentEndpoint, logEnvironmentInfo } from "../config/environment";

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  accessToken: string;
  tokenExpiry: Date;
}

// Alternative auth service using redirect flow instead of popup
class AuthServiceRedirect {
  private msalInstance: PublicClientApplication;
  private currentUser: UserProfile | null = null;

  constructor() {
    this.msalInstance = new PublicClientApplication(msalConfig);
  }

  async initialize(): Promise<void> {
    try {
      logEnvironmentInfo();
      await this.msalInstance.initialize();
      await this.handleRedirectPromise();
      this.loadCachedUser();
    } catch (error) {
      console.error("Failed to initialize MSAL:", error);
    }
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
        
        // Always use cached user - no expiry checking
        // Cache will only be replaced when user logs in again
        this.currentUser = user;
        console.log("✅ Loaded cached user (never expires):", user.email);
      }
    } catch (error) {
      console.error("Error loading cached user:", error);
      localStorage.removeItem('hco-microsoft-user');
    }
  }

  async login(): Promise<UserProfile> {
    try {
      console.log('🔑 Starting Microsoft login with redirect...');
      console.log('📋 MSAL Config:', {
        clientId: msalConfig.auth.clientId,
        authority: msalConfig.auth.authority,
        redirectUri: msalConfig.auth.redirectUri,
      });

      // Try silent authentication first
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
          console.log("⚠️ Silent authentication failed, using redirect:", silentError);
        }
      }

      // Use redirect flow instead of popup
      console.log('🌐 Starting Microsoft login redirect...');
      await this.msalInstance.acquireTokenRedirect(loginRequest);
      
      // This will redirect the page, so we won't reach this point
      throw new Error("Redirect initiated");
      
    } catch (error) {
      console.error("❌ Microsoft login failed:", error);
      
      if (error instanceof Error) {
        if (error.message === "Redirect initiated") {
          throw error; // Don't show this as an error
        }
        throw new Error(`Microsoft login failed: ${error.message}`);
      }
      
      throw new Error("Microsoft login failed. Please try again.");
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

    // Set expiry to a far future date (effectively never expires)
    // Cache will only be replaced when user logs in again
    const expiryTime = new Date();
    expiryTime.setFullYear(expiryTime.getFullYear() + 10); // 10 years from now

    const user: UserProfile = {
      id: account.homeAccountId,
      email: account.username,
      name: userProfile.displayName || account.name || account.username,
      accessToken: response.accessToken,
      tokenExpiry: expiryTime,
    };

    this.currentUser = user;
    localStorage.setItem('hco-microsoft-user', JSON.stringify(user));
    
    // Sync with backend auth cache
    await this.syncWithBackend(user);
    
    return user;
  }

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
    }
  }

  async logout(): Promise<void> {
    try {
      const accounts = this.msalInstance.getAllAccounts();
      if (accounts.length > 0) {
        // Use logoutRedirect to properly clear accounts
        await this.msalInstance.logoutRedirect();
      }
    } catch (error) {
      console.error("Error during logout:", error);
    }

    this.currentUser = null;
    localStorage.removeItem('hco-microsoft-user');
    localStorage.removeItem('hco-user');
  }

  getCurrentUser(): UserProfile | null {
    return this.currentUser;
  }

  isAuthenticated(): boolean {
    // Simply check if we have a current user - no expiry checking
    // Cache never expires and is only replaced when user logs in again
    return this.currentUser !== null;
  }
}

// Export alternative service
export const authServiceRedirect = new AuthServiceRedirect();