import { useState, useEffect } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  useNavigate,
} from "react-router-dom";
import UploadCertificate from "./components/UploadCertificate";
import GenerateCertificate from "./components/GenerateCertificate";
import ChatInterface from "./components/ChatInterface";
import ProtectedRoute from "./components/ProtectedRoute";
import NewNavbar from "./components/NewNavbar";
import { authService } from "./services/authService";
import type { UserProfile } from "./services/authService";
import { apiService } from "./services/apiService";
import "./App.css";
import { getApiUrl } from "./config/env";


interface User {
  email: string;
  name?: string;
  id?: string;
  isMicrosoftAuth?: boolean;
}

function AppContent() {
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const navigate = useNavigate();

  // Initialize authentication and check for saved user session
  useEffect(() => {
    const initializeAuth = async () => {
      await authService.initialize();
      
      // Check for Microsoft auth first
      const microsoftUser = authService.getCurrentUser();
      if (microsoftUser && authService.isAuthenticated()) {
        try {
          // Validate cached session against backend rules (drive access + allowlist)
          const resp = await fetch(`${getApiUrl()}/auth/validate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ access_token: microsoftUser.accessToken }),
          });
          const data = await resp.json();
          if (!resp.ok || !data?.allowed) {
            // If backend explicitly denies, enforce it.
            // If backend is temporarily failing (e.g. schema mismatch 500), do NOT hard-block the user:
            // generation is still protected server-side by token + OneDrive access checks.
            const msg = String(data?.message || "");
            const looksLikeTransientBackendError =
              !resp.ok && (msg.includes("schema") || msg.includes("Handler response") || msg.includes("Internal"));
            if (!looksLikeTransientBackendError) {
              await authService.logout();
              setUser(null);
              localStorage.removeItem("hco-user");
              setAuthError(data?.message || "Access denied. Please sign in with an allowed account.");
              return;
            }
            setAuthError("⚠️ Unable to confirm drive access right now. You can continue, but generation may fail until the backend is healthy.");
          }

        setUser({
          email: microsoftUser.email,
          name: microsoftUser.name,
          id: microsoftUser.id,
          isMicrosoftAuth: true,
        });
        return;
        } catch (e) {
          // Backend may be temporarily unavailable; don't hard-block the UI.
          setUser({
            email: microsoftUser.email,
            name: microsoftUser.name,
            id: microsoftUser.id,
            isMicrosoftAuth: true,
          });
          setAuthError(`⚠️ Login validation failed (backend). You can continue, but generation may fail. ${e instanceof Error ? e.message : ""}`);
          return;
        }
      }

      // Fallback to legacy auth
      const savedUser = localStorage.getItem("hco-user");
      if (savedUser) {
        try {
          const userData = JSON.parse(savedUser);
          setUser({ ...userData, isMicrosoftAuth: false });
        } catch {
          localStorage.removeItem("hco-user");
        }
      }
    };

    initializeAuth();
  }, []);

  const handleLogin = async (username: string, password: string) => {
    setAuthLoading(true);
    setAuthError("");

    try {
      // Call the simple login endpoint
      const loginResult = await apiService.login(username, password);
      
      if (loginResult.success && loginResult.token) {
        // Store session token
        localStorage.setItem('hco_session_token', loginResult.token);
        localStorage.setItem('hco_session_expires', loginResult.expires_at?.toString() || '0');

        // Set user state
        setUser({
          email: loginResult.user_email || username,
          name: username,
          id: username,
          isMicrosoftAuth: false,
        });
        
        // Store user in localStorage
        localStorage.setItem('hco-user', JSON.stringify({
          email: loginResult.user_email || username,
          name: username,
          id: username,
          isMicrosoftAuth: false,
        }));
        
        // Navigate to generate page
        navigate('/generate');
      } else {
        setAuthError(loginResult.message || "Invalid username or password");
      }
    } catch (error) {
      console.error("Login error:", error);
      setAuthError(error instanceof Error ? error.message : "Login failed. Please try again.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleMicrosoftLogin = async (microsoftUser: UserProfile) => {
    setAuthLoading(true);
    setAuthError("");
    try {
      // Ask backend to validate that this user can access the configured OneDrive folder.
      let allowed: boolean | null = null;
      let denyMessage = "";
      try {
        const resp = await fetch(`${getApiUrl()}/auth/validate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ access_token: microsoftUser.accessToken }),
        });
        const data = await resp.json();
        if (resp.ok && data?.allowed === true) {
          allowed = true;
        } else if (data?.allowed === false) {
          allowed = false;
          denyMessage = data?.message || "Access denied. You do not have access to generate certificates.";
        } else {
          // Unknown backend failure (e.g. schema mismatch). Treat as "unknown" and let backend enforce on generation.
          allowed = null;
          setAuthError("⚠️ Unable to confirm drive access right now. You can continue, but generation may fail until the backend is healthy.");
        }
      } catch (e) {
        allowed = null;
        setAuthError(`⚠️ Unable to confirm drive access right now. You can continue, but generation may fail. ${e instanceof Error ? e.message : ""}`);
      }

      if (allowed === false) {
        await authService.logout();
        setUser(null);
        localStorage.removeItem("hco-user");
        setAuthError(denyMessage);
        return;
      }

    const userData: User = {
      email: microsoftUser.email,
      name: microsoftUser.name,
      id: microsoftUser.id,
      isMicrosoftAuth: true,
    };
    setUser(userData);
    navigate("/generate");
    } catch (e) {
      await authService.logout();
      setUser(null);
      setAuthError(`Login validation failed. ${e instanceof Error ? e.message : ""}`);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    if (user?.isMicrosoftAuth) {
      await authService.logout();
    }
    setUser(null);
    localStorage.removeItem("hco-user");
    navigate("/");
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 font-quicksand">
      <NewNavbar user={user} onLogout={handleLogout} />

      <main className="flex-1 bg-gray-50">
        <Routes>
          <Route path="/" element={<UploadCertificate user={user} />} />
          <Route
            path="/generate"
            element={
              <ProtectedRoute
                user={user}
                onLogin={handleLogin}
                onMicrosoftLogin={handleMicrosoftLogin}
                loading={authLoading}
                error={authError}
              >
                <GenerateCertificate />
              </ProtectedRoute>
            }
          />
          <Route path="/chat" element={<ChatInterface user={user} />} />
        </Routes>
      </main>

      {/* <Footer /> */}
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
