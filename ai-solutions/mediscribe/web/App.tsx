import React from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Login } from './components/Login';
import { Dashboard } from './components/Dashboard';

const AppContent: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-slate-200 border-t-blue-600 mb-4"></div>
          <p className="text-slate-600">Loading...</p>
        </div>
      </div>
    );
  }

  return isAuthenticated ? <Dashboard /> : <Login />;
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;

