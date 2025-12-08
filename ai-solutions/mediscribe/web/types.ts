// User and Authentication Types
export interface User {
  username: string;
  role: string;
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, role?: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// Audio and Transcript Types
export interface SoapNote {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
}

export interface TranscriptListItem {
  id: string;
  title: string;
  status: 'processing' | 'completed' | 'failed';
  created_at: string;
  summary?: string;
}

export interface Transcript {
  id: string;
  title: string;
  status: 'processing' | 'completed' | 'failed';
  summary?: string;
  soap_note?: SoapNote;
  created_at: string;
  chats: ChatMessage[];
}

// Chat Types
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  message: string;
  created_at: string;
}

export interface ChatMessageInput {
  role: 'user' | 'model';
  text: string;
}
