import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/providers/auth-provider";

export function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/" replace state={{ from: location }} />;
  }

  return children;
}
