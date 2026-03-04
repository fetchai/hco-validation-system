import React, { useState } from "react";
import { authService } from "../services/authService";
import type { UserProfile } from "../services/authService";

interface MicrosoftLoginProps {
  onLoginSuccess: (user: UserProfile) => void;
  onError: (error: string) => void;
  disabled?: boolean;
}

const MicrosoftLogin: React.FC<MicrosoftLoginProps> = ({
  onLoginSuccess,
  onError,
  disabled = false,
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleMicrosoftLogin = async () => {
    setIsLoading(true);
    try {
      console.log('🔄 Starting Microsoft login...');
      const user = await authService.login();
      console.log('✅ Microsoft login successful:', user);
      onLoginSuccess(user);
    } catch (error) {
      console.error('❌ Microsoft login error:', error);
      const errorMessage = error instanceof Error ? error.message : "Microsoft login failed";
      onError(`Microsoft login failed: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleMicrosoftLogin}
      disabled={disabled || isLoading}
      className="w-full inline-flex items-center justify-center h-11 bg-[#0078d4] text-white text-sm font-medium font-quicksand tracking-wide hover:bg-[#106ebe] transition-colors disabled:bg-[#b8cbbf] disabled:cursor-not-allowed border border-[#0078d4] hover:border-[#106ebe]"
    >
      {isLoading ? (
        <>
          <div className="mr-2 h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          <span>Signing in with Microsoft...</span>
        </>
      ) : (
        <>
          <svg
            className="mr-2 w-5 h-5"
            viewBox="0 0 23 23"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M1 1h10v10H1z" fill="#f25022"/>
            <path d="M12 1h10v10H12z" fill="#00a4ef"/>
            <path d="M1 12h10v10H1z" fill="#ffb900"/>
            <path d="M12 12h10v10H12z" fill="#7fba00"/>
          </svg>
          <span>Sign in with Microsoft</span>
        </>
      )}
    </button>
  );
};

export default MicrosoftLogin;