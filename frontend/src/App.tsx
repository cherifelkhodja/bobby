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
import { CvGeneratorBeta } from './pages/CvGeneratorBeta';
import { QuotationGenerator } from './pages/QuotationGenerator';
import HRDashboard from './pages/HRDashboard';
import CreateJobPosting from './pages/CreateJobPosting';
import EditJobPosting from './pages/EditJobPosting';
import JobPostingDetails from './pages/JobPostingDetails';
import PublicApplication from './pages/PublicApplication';
import { MyBoondOpportunities } from './pages/MyBoondOpportunities';
import PublishedOpportunityDetail from './pages/PublishedOpportunityDetail';
import { OpportunityDetail } from './pages/OpportunityDetail';
import ProposeCandidate from './pages/ProposeCandidate';
import { ContractManagement } from './pages/ContractManagement';
import ContractDetail from './pages/ContractDetail';
import ComplianceDashboard from './pages/ComplianceDashboard';
import Portal from './pages/Portal';
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
      <Route path="/postuler/:token" element={<PublicApplication />} />
      <Route path="/portal/:token" element={<Portal />} />

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
        <Route path="opportunities/:id/proposer" element={<ProposeCandidate />} />
        <Route path="my-cooptations" element={<MyCooptations />} />
        <Route path="profile" element={<Profile />} />
        <Route
          path="cv-generator"
          element={
            <ProtectedRoute allowedRoles={['admin', 'commercial', 'rh']}>
              <CvGeneratorBeta />
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
          path="my-boond-opportunities/:publishedId"
          element={
            <ProtectedRoute allowedRoles={['admin', 'commercial']}>
              <PublishedOpportunityDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="contracts"
          element={
            <ProtectedRoute allowedRoles={['admin', 'adv', 'commercial']}>
              <ContractManagement />
            </ProtectedRoute>
          }
        />
        <Route
          path="contracts/:id"
          element={
            <ProtectedRoute allowedRoles={['admin', 'adv', 'commercial']}>
              <ContractDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="compliance"
          element={
            <ProtectedRoute allowedRoles={['admin', 'adv']}>
              <ComplianceDashboard />
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
        <Route
          path="rh"
          element={
            <ProtectedRoute allowedRoles={['admin', 'rh']}>
              <HRDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="rh/annonces/nouvelle/:oppId"
          element={
            <ProtectedRoute allowedRoles={['admin', 'rh']}>
              <CreateJobPosting />
            </ProtectedRoute>
          }
        />
        <Route
          path="rh/annonces/edit/:postingId"
          element={
            <ProtectedRoute allowedRoles={['admin', 'rh']}>
              <EditJobPosting />
            </ProtectedRoute>
          }
        />
        <Route
          path="rh/annonces/:postingId"
          element={
            <ProtectedRoute allowedRoles={['admin', 'rh']}>
              <JobPostingDetails />
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
