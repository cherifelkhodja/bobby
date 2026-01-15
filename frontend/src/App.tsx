import { Routes, Route, Navigate } from 'react-router-dom';

import { useAuthStore } from './stores/authStore';
import { Layout } from './components/layout/Layout';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { ForgotPassword } from './pages/ForgotPassword';
import { ResetPassword } from './pages/ResetPassword';
import { AcceptInvitation } from './pages/AcceptInvitation';
import { Dashboard } from './pages/Dashboard';
import { Opportunities } from './pages/Opportunities';
import { MyCooptations } from './pages/MyCooptations';
import { Profile } from './pages/Profile';
import { Admin } from './pages/Admin';
import { CvTransformer } from './pages/CvTransformer';
import { QuotationGenerator } from './pages/QuotationGenerator';
import { MyBoondOpportunities } from './pages/MyBoondOpportunities';
import { OpportunityDetail } from './pages/OpportunityDetail';
import type { UserRole } from './types';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
  allowedRoles?: UserRole[];
}

function ProtectedRoute({ children, requireAdmin = false, allowedRoles }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requireAdmin && user?.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }

  if (allowedRoles && user?.role && !allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/accept-invitation" element={<AcceptInvitation />} />

      {/* Protected routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="opportunities" element={<Opportunities />} />
        <Route path="opportunities/:id" element={<OpportunityDetail />} />
        <Route path="my-cooptations" element={<MyCooptations />} />
        <Route path="profile" element={<Profile />} />
        <Route
          path="cv-transformer"
          element={
            <ProtectedRoute allowedRoles={['admin', 'commercial', 'rh']}>
              <CvTransformer />
            </ProtectedRoute>
          }
        />
        <Route
          path="my-boond-opportunities"
          element={
            <ProtectedRoute allowedRoles={['admin', 'commercial']}>
              <MyBoondOpportunities />
            </ProtectedRoute>
          }
        />
        <Route
          path="admin"
          element={
            <ProtectedRoute requireAdmin>
              <Admin />
            </ProtectedRoute>
          }
        />
        <Route
          path="quotation-generator"
          element={
            <ProtectedRoute requireAdmin>
              <QuotationGenerator />
            </ProtectedRoute>
          }
        />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
