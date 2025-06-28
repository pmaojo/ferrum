import { useQuery } from '@tanstack/react-query';
import { User } from '../types/User';

interface GetuserParams {
  
  userId: string; // Using string as default type
  
}

export const useGetuser = ({ userId }: GetuserParams) => {
  return useQuery<User>(
    ['getUser', userId],
    async () => {
      const response = await fetch(`/api/users/getuser`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ userId }),
      });
      
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      
      return response.json();
    },
    {
      enabled: !!userId,
    }
  );
};
