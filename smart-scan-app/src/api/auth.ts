import apiClient from './client';
import { saveTokens, clearTokens } from '../storage/tokenStorage';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  name: string;
  email: string;
  password: string;
  phone: string;
  age: number;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: {
    id: string;
    name: string;
    email: string;
  };
}

export const login = async (email: string, password: string): Promise<AuthResponse> => {
  const response = await apiClient.post<AuthResponse>('/api/auth/login', {
    email,
    password,
  });

  const { access_token, refresh_token } = response.data;
  await saveTokens(access_token, refresh_token);

  return response.data;
};

export const signup = async (
  name: string,
  email: string,
  password: string,
  phone: string,
  age: number
): Promise<void> => {
  await apiClient.post('/api/auth/register', {
    name,
    email,
    password,
    phone,
    age,
  });
};

export const refreshToken = async (refreshToken: string): Promise<AuthResponse> => {
  const response = await apiClient.post<AuthResponse>('/api/auth/refresh', {
    refresh_token: refreshToken,
  });

  const { access_token, refresh_token: newRefreshToken } = response.data;
  await saveTokens(access_token, newRefreshToken);

  return response.data;
};

export const logout = async (): Promise<void> => {
  try {
    await apiClient.post('/api/auth/logout');
  } catch (error) {
  } finally {
    try {
      await clearTokens();
    } catch (clearError) {
      console.error('Failed to clear tokens during logout:', clearError);
    }
  }
};