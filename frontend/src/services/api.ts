import { User, ConversationSummary, AnalyticsSummary, ChatMessage, EvalBenchmarkReport } from '../types';

const API_BASE = 'http://localhost:8000/api/v1';
export const WS_BASE = 'ws://localhost:8000/api/v1/chat/ws';

export const getAuthToken = (): string | null => {
  return localStorage.getItem('nexus_token');
};

export const setAuthToken = (token: string) => {
  localStorage.setItem('nexus_token', token);
};

export const clearAuthToken = () => {
  localStorage.removeItem('nexus_token');
};

const getHeaders = (isJson = true) => {
  const headers: Record<string, string> = {};
  if (isJson) headers['Content-Type'] = 'application/json';
  const token = getAuthToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
};

export const api = {
  // Authentication
  async register(email: string, username: string, password: string):Promise<{ access_token: string; user: User }> {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(err.detail || 'Registration failed');
    }
    return res.json();
  },

  async login(username_or_email: string, password: string): Promise<{ access_token: string; user: User }> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username_or_email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail || 'Login failed');
    }
    return res.json();
  },

  async getMe(): Promise<User> {
    const res = await fetch(`${API_BASE}/auth/me`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Not authenticated');
    return res.json();
  },

  // Conversations
  async getConversations(): Promise<ConversationSummary[]> {
    const res = await fetch(`${API_BASE}/chat/conversations`, { headers: getHeaders() });
    if (!res.ok) return [];
    return res.json();
  },

  async getConversation(id: string): Promise<{ id: string; title: string; messages: ChatMessage[] }> {
    const res = await fetch(`${API_BASE}/chat/conversations/${id}`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Conversation not found');
    return res.json();
  },

  async deleteConversation(id: string): Promise<void> {
    await fetch(`${API_BASE}/chat/conversations/${id}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
  },

  // Feedback
  async submitFeedback(messageId: string, rating: number, comment?: string): Promise<void> {
    await fetch(`${API_BASE}/chat/feedback`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ message_id: messageId, rating, comment }),
    });
  },

  // Export
  getExportUrl(conversationId: string, format: 'text' | 'pdf'): string {
    return `${API_BASE}/chat/export/${conversationId}?format=${format}`;
  },

  // Analytics & Evaluation Benchmark
  async getAnalytics(): Promise<AnalyticsSummary> {
    const res = await fetch(`${API_BASE}/analytics/metrics`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to load metrics');
    return res.json();
  },

  async getEvaluationReport(): Promise<EvalBenchmarkReport> {
    const res = await fetch(`${API_BASE}/analytics/eval`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to load evaluation benchmark report');
    return res.json();
  },

  async runEvaluationBenchmark(): Promise<EvalBenchmarkReport> {
    const res = await fetch(`${API_BASE}/analytics/eval/run`, {
      method: 'POST',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to execute evaluation benchmark');
    return res.json();
  },

  async getCircuitBreakerStatus(): Promise<{ state: string; failure_count: number; recovery_timeout_seconds: number } | null> {
    const res = await fetch(`${API_BASE}/analytics/circuit-breaker`, { headers: getHeaders() });
    if (!res.ok) return null;
    return res.json();
  },

  async verifyAuditChain(): Promise<{ valid: boolean; total_records: number; message: string } | null> {
    const res = await fetch(`${API_BASE}/audit/verify`, { headers: getHeaders() });
    if (!res.ok) return null;
    return res.json();
  },

  // Models
  async getModels(): Promise<{ current_model: string; available_models: string[] }> {
    const res = await fetch(`${API_BASE}/models`, { headers: getHeaders() });
    if (!res.ok) return { current_model: 'nexus-llama3-8b-v1', available_models: ['nexus-llama3-8b-v1'] };
    return res.json();
  },

  async switchModel(model_name: string): Promise<void> {
    await fetch(`${API_BASE}/models/switch`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ model_name }),
    });
  },

  // File Upload
  async uploadFile(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    const token = getAuthToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}/files/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) throw new Error('File upload failed');
    return res.json();
  },

  // Voice
  async transcribeAudio(audioBlob: Blob): Promise<{ text: string }> {
    const formData = new FormData();
    formData.append('file', audioBlob, 'recording.wav');
    const headers: Record<string, string> = {};
    const token = getAuthToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}/voice/transcribe`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) throw new Error('Transcription failed');
    return res.json();
  },

  async synthesizeSpeech(text: string): Promise<Blob> {
    const res = await fetch(`${API_BASE}/voice/synthesize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error('Synthesis failed');
    return res.blob();
  },

  // SSE Streaming Fallback
  async streamChatSSE(
    sessionId: string,
    payload: { message: string; use_rag?: boolean; use_tools?: boolean; model_name?: string },
    onEvent: (data: any) => void
  ): Promise<void> {
    const res = await fetch(`${API_BASE}/chat/sse/${sessionId}`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(`SSE request failed with status: ${res.status}`);
    }

    if (!res.body) {
      throw new Error('ReadableStream not supported or empty body');
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data:')) {
          const jsonStr = trimmed.slice(5).trim();
          if (jsonStr) {
            try {
              const data = JSON.parse(jsonStr);
              onEvent(data);
            } catch (err) {
              console.warn('Failed to parse SSE data frame:', jsonStr, err);
            }
          }
        }
      }
    }

    if (buffer.trim().startsWith('data:')) {
      const jsonStr = buffer.trim().slice(5).trim();
      if (jsonStr) {
        try {
          const data = JSON.parse(jsonStr);
          onEvent(data);
        } catch {}
      }
    }
  },
};
