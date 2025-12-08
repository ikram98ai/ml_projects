const API_BASE = '/api/v1';

export interface SoapNote {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
}

export interface TranscriptResponse {
  id: string;
  status: 'processing' | 'completed' | 'failed';
  summary?: string;
  soap_note?: SoapNote;
  created_at: string;
}

export interface UploadResponse {
  id: string;
  status: string;
}

export interface AskResponse {
  answer: string;
}

export const uploadAudio = async (audioBlob: Blob, token: string): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.wav');

  const response = await fetch(`${API_BASE}/audio/upload`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    throw new Error('Failed to upload audio');
  }

  return response.json();
};

export const getTranscript = async (transcriptId: string, token: string): Promise<TranscriptResponse> => {
  const response = await fetch(`${API_BASE}/audio/${transcriptId}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to get transcript');
  }

  return response.json();
};

export const askQuestion = async (
  transcriptId: string,
  question: string,
  token: string
): Promise<AskResponse> => {
  const response = await fetch(`${API_BASE}/audio/${transcriptId}/ask?question=${encodeURIComponent(question)}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to ask question');
  }

  return response.json();
};
