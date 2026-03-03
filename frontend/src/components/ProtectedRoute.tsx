import { ReactNode } from "react";

interface ProtectedRouteProps {
  isAuthenticated: boolean;
  fallback: ReactNode;
  children: ReactNode;
}

export default function ProtectedRoute({
  isAuthenticated,
  fallback,
  children,
}: ProtectedRouteProps) {
  if (!isAuthenticated) {
    return <>{fallback}</>;
  }
  return <>{children}</>;
}
