import { User, TranscriptListItem, Transcript } from '../types';

const API_BASE = 'http://localhost:8000/api/v1';

// Response Types
export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UploadResponse {
  id: string;
  status: string;
}

export interface TranscriptStatus {
    id: string;
    status: string;
}

export interface AskResponse {
  answer: string;
}

// Helper function to get auth headers
const getAuthHeaders = (token: string): HeadersInit => ({
  'Authorization': `Bearer ${token}`,
});

// Authentication API
export const login = async (username: string, password: string): Promise<TokenResponse> => {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);

  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(error.detail || 'Invalid username or password');
  }

  return response.json();
};

export const register = async (
  username: string,
  password: string,
  role: string = 'clinician'
): Promise<TokenResponse> => {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ username, password, role }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Registration failed' }));
    throw new Error(error.detail || 'Failed to create account');
  }

  return response.json();
};

// Audio/Transcript API
export const uploadAudio = async (audioBlob: Blob, title: string, token: string): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('title', title);
  formData.append('file', audioBlob, 'recording.wav');

  const response = await fetch(`${API_BASE}/audio/upload`, {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Failed to upload audio');
  }

  return response.json();
};


export const listTranscripts = async (token: string): Promise<TranscriptListItem[]> => {
  const response = await fetch(`${API_BASE}/audio/transcripts`, {
    method: 'GET',
    headers: getAuthHeaders(token),
  });

  if (!response.ok) {
    throw new Error('Failed to fetch transcripts');
  }

  return response.json();
};

export const getTranscript = async (transcriptId: string, token: string): Promise<Transcript> => {
  const response = await fetch(`${API_BASE}/audio/${transcriptId}`, {
    method: 'GET',
    headers: getAuthHeaders(token),
  });

  if (!response.ok) {
    throw new Error('Failed to get transcript');
  }

  return response.json();
};

export const getTranscriptStatus = async (transcriptId: string, token: string): Promise<TranscriptStatus> => {
    const response = await fetch(`${API_BASE}/audio/${transcriptId}/status`, {
        method: 'GET',
        headers: getAuthHeaders(token),
    });

    if (!response.ok) {
        throw new Error('Failed to get transcript status');
    }

    return response.json();
}

export const askQuestion = async (
  transcriptId: string,
  question: string,
  token: string
): Promise<AskResponse> => {
  const response = await fetch(
    `${API_BASE}/audio/${transcriptId}/ask?question=${encodeURIComponent(question)}`,
    {
      method: 'POST',
      headers: getAuthHeaders(token),
    }
  );

  if (!response.ok) {
    throw new Error('Failed to ask question');
  }

  return response.json();
};

