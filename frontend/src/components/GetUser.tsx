import React from 'react';
import { useGetuser } from '../hooks/useGetuser';

interface GetuserViewProps {
  
  userId: string; // Using string as default type
  
}

export const GetuserView: React.FC<GetuserViewProps> = ({ userId }) => {
  const { data, isLoading, error } = useGetuser({ userId });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {(error as Error).message}</div>;
  if (!data) return null;

  return (
    <div className="getuser-view">
      <h2>User</h2>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
};
