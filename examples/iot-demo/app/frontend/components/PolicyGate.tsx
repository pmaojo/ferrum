import React from 'react';
import { usePolicy } from '../hooks/usePolicy';

interface Props { policy?: string; children: React.ReactNode; }
export const PolicyGate: React.FC<Props> = ({ policy, children }) => {
  const allowed = policy ? usePolicy(policy) : true;
  if (!allowed) return null;
  return <>{children}</>;
};
