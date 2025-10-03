// Global type definitions for React Native
declare var __DEV__: boolean;

export interface User {
  id: string;
  email: string;
  username: string;
  name: string;
}

export interface Document {
  id: string;
  filename: string;
  upload_date: string;
  file_size: number;
  status: 'processing' | 'completed' | 'failed';
  s3_key?: string;
}

export interface ChatMessage {
  id: string;
  content: string;
  is_user_message: boolean;
  created_at: string;
  response_time_ms?: number;
  token_count?: number;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  document?: Document;
  messages: ChatMessage[];
}

export interface SessionInsight {
  session_id: string;
  document_name: string;
  session_title: string;
  total_qa_pairs: number;
  session_duration: string;
  status: 'completed' | 'processing' | 'failed';
  insights: {
    strength: string;
    weakness: string;
    opportunity: string;
    threat: string;
  };
  created_at: string;
  updated_at: string;
}

export interface TutoringQuestion {
  id: string;
  text: string;
  created_at: string;
}

export interface ApiResponse<T = any> {
  data: T;
  status: number;
  statusText: string;
}

export interface ApiError {
  response?: {
    status: number;
    data: {
      error?: string;
      details?: string;
      [key: string]: any;
    };
  };
  message: string;
}