export enum UserRole {
  DOCTOR = 'DOCTOR',
  ADMIN = 'ADMIN'
}

export interface Patient {
  id: string;
  name: string;
  age: number;
  mrn: string; // Medical Record Number
}

export interface SoapNote {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
}

export interface ConsultationRecord {
  id: string;
  timestamp: Date;
  patientId: string;
  transcript: string;
  summary: SoapNote;
  audioBlob?: Blob;
}

export interface ChatMessage {
  role: 'user' | 'model';
  text: string;
}
