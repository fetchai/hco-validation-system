import React from 'react';
import Login from './Login';
import type { UserProfile } from '../services/authService';

interface ProtectedRouteProps {
  children: React.ReactNode;
  user: { email: string; name?: string; id?: string; isMicrosoftAuth?: boolean } | null;
  onLogin: (email: string, password: string) => void;
  onMicrosoftLogin: (user: UserProfile) => void;
  loading: boolean;
  error: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  user, 
  onLogin, 
  onMicrosoftLogin,
  loading, 
  error 
}) => {
  if (!user) {
    return (
      <Login
        onLogin={onLogin}
        onMicrosoftLogin={onMicrosoftLogin}
        loading={loading}
        error={error}
      />
    );
  }

  return <>{children}</>;
};

export default ProtectedRoute;