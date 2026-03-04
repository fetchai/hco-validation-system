import React, { useState } from "react";
import MicrosoftLogin from "./MicrosoftLogin";
import type { UserProfile } from "../services/authService";

interface LoginProps {
  onLogin: (email: string, password: string) => void;
  onMicrosoftLogin: (user: UserProfile) => void;
  loading: boolean;
  error: string;
}

const Login: React.FC<LoginProps> = ({ onLogin, onMicrosoftLogin, loading, error }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [authError, setAuthError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError("");
    onLogin(email, password);
  };

  const handleMicrosoftLoginSuccess = (user: UserProfile) => {
    setAuthError("");
    onMicrosoftLogin(user);
  };

  const handleMicrosoftLoginError = (errorMessage: string) => {
    setAuthError(errorMessage);
  };

  return (
    <div className="min-h-screen bg-white">
      <div className="w-full bg-[#358743] text-white py-6 lg:py-10 text-center">
        <h1 className="text-xl sm:text-2xl lg:text-3xl font-semibold font-quicksand px-4">
          Login
        </h1>
        <p className="mt-2 lg:mt-3 text-xs sm:text-sm lg:text-base max-w-2xl mx-auto opacity-90 px-4 font-quicksand">
          Sign in to access certificate generation and HCO assistant.
        </p>
      </div>

      <div className="py-6 lg:py-10 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md mx-auto">
          <div className="bg-[#f7fbf8] border border-[#e0efe4] shadow-sm p-4 sm:p-6 lg:p-8">
            <div className="flex items-center gap-3 mb-4 sm:mb-6">
              <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-full bg-[#e0efe4] flex items-center justify-center">
                <img
                  src="/HCO-Logo.avif"
                  alt="HCO Ltd"
                  className="h-6 sm:h-8 w-auto"
                />
              </div>
              <div>
                <h2 className="text-base sm:text-lg font-semibold text-[#4f8f5e] font-quicksand">
                  Welcome to HCO
                </h2>
                <p className="text-xs text-[#7aa487] font-quicksand">
                  Sign in to continue to certificate tools.
                </p>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
              {(error || authError) && (
                <div className="border-l-4 px-3 py-2 text-xs sm:text-sm border-[#c85c5c] bg-[#fceced] text-[#8a3131] flex items-start gap-2">
                  <svg width="16" height="16" className="sm:w-4 sm:h-4 mt-0.5" viewBox="0 0 24 24" fill="none">
                    <circle
                      cx="12"
                      cy="12"
                      r="10"
                      fill="currentColor"
                      fillOpacity="0.1"
                    />
                    <path
                      d="m15 9-6 6m0-6 6 6"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span>{error || authError}</span>
                </div>
              )}

              <div className="flex flex-col">
                <label
                  htmlFor="email"
                  className="mb-2 text-xs sm:text-sm font-medium text-[#4f8f5e] font-quicksand"
                >
                  Username
                </label>
                <div className="flex items-center bg-[#e8f0eb] text-[#4f8f5e] px-3 sm:px-4 h-10 sm:h-11">
                  <svg
                    className="w-4 h-4 mr-2 sm:mr-3 text-[#7aa487]"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <path
                      d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <circle
                      cx="12"
                      cy="7"
                      r="4"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <input
                    type="text"
                    id="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={loading}
                    placeholder="hcoadmin"
                    className="flex-1 bg-transparent outline-none text-xs sm:text-sm placeholder-[#9bb7a4] font-quicksand"
                  />
                </div>
              </div>

              <div className="flex flex-col">
                <label
                  htmlFor="password"
                  className="mb-2 text-sm font-medium text-[#4f8f5e] font-quicksand"
                >
                  Password
                </label>
                <div className="flex items-center bg-[#e8f0eb] text-[#4f8f5e] px-4 h-11">
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    className="mr-3 text-[#7aa487]"
                  >
                    <rect
                      x="3"
                      y="11"
                      width="18"
                      height="11"
                      rx="2"
                      ry="2"
                      stroke="currentColor"
                      strokeWidth="2"
                    />
                    <circle cx="12" cy="16" r="1" fill="currentColor" />
                    <path
                      d="M7 11V7a5 5 0 0 1 10 0v4"
                      stroke="currentColor"
                      strokeWidth="2"
                    />
                  </svg>
                  <input
                    type={showPassword ? "text" : "password"}
                    id="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={loading}
                    placeholder="Enter your password"
                    className="flex-1 bg-transparent outline-none text-sm placeholder-[#9bb7a4] font-quicksand"
                  />
                  <button
                    type="button"
                    className="ml-2 text-xs text-[#4f8f5e]"
                    onClick={() => setShowPassword(!showPassword)}
                    disabled={loading}
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                className="w-full inline-flex items-center justify-center h-11 bg-[#4f8f5e] text-white text-sm font-medium font-quicksand tracking-wide hover:bg-[#3f724d] transition-colors disabled:bg-[#b8cbbf] disabled:cursor-not-allowed"
                disabled={loading || !email || !password}
              >
                {loading ? (
                  <>
                    <div className="mr-2 h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In</span>
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      className="ml-2"
                    >
                      <path
                        d="m9 18 6-6-6-6"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </>
                )}
              </button>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t border-[#b8cbbf]" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-[#f7fbf8] px-2 text-[#9bb7a4] font-quicksand">Or</span>
                </div>
              </div>

              <MicrosoftLogin
                onLoginSuccess={handleMicrosoftLoginSuccess}
                onError={handleMicrosoftLoginError}
                disabled={loading}
              />

              <p className="mt-2 text-[11px] text-center text-[#9bb7a4] font-quicksand">
                Secure authentication powered by HCO Ltd
              </p>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
