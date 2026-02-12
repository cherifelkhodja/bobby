import { apiClient } from './client';
import { useAuthStore } from '../stores/authStore';

export interface CvGeneratorParseResponse {
  success: boolean;
  data: Record<string, unknown>;
  model_used: string;
}

export interface SSEProgressEvent {
  step: 'extracting' | 'ai_parsing' | 'validating' | 'complete';
  message: string;
  percent: number;
}

export interface SSECompleteEvent {
  success: boolean;
  data: Record<string, unknown>;
  model_used: string;
}

export interface SSEErrorEvent {
  message: string;
}

export interface ParseCvStreamCallbacks {
  onProgress: (event: SSEProgressEvent) => void;
  onComplete: (event: SSECompleteEvent) => void;
  onError: (message: string) => void;
}

const API_URL = import.meta.env.VITE_API_URL || '';

export const cvGeneratorApi = {
  /**
   * Upload a CV file and get parsed section-based JSON.
   * The JSON is designed for frontend DOCX generation.
   */
  parseCv: async (file: File): Promise<CvGeneratorParseResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<CvGeneratorParseResponse>(
      '/cv-generator/parse',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );
    return response.data;
  },

  /**
   * Upload a CV file and get parsed JSON via SSE streaming.
   * Provides progressive feedback through callbacks.
   */
  parseCvStream: async (
    file: File,
    callbacks: ParseCvStreamCallbacks
  ): Promise<void> => {
    const formData = new FormData();
    formData.append('file', file);

    const { tokens } = useAuthStore.getState();
    const token = tokens?.access_token;

    if (!token) {
      callbacks.onError('Non authentifié');
      return;
    }

    const response = await fetch(
      `${API_URL}/api/v1/cv-generator/parse-stream`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      }
    );

    if (!response.ok) {
      // Handle HTTP errors (auth, validation, etc.)
      let errorMessage = `Erreur HTTP ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch {
        // Ignore JSON parse error
      }

      // If 401, try refreshing token and retrying once
      if (response.status === 401) {
        const refreshed = await tryRefreshAndRetry(file, callbacks);
        if (!refreshed) {
          callbacks.onError('Session expirée. Veuillez vous reconnecter.');
        }
        return;
      }

      callbacks.onError(errorMessage);
      return;
    }

    if (!response.body) {
      callbacks.onError('Le navigateur ne supporte pas le streaming');
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      let reading = true;
      while (reading) {
        const { done, value } = await reader.read();
        if (done) { reading = false; break; }

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages (separated by double newlines)
        const messages = buffer.split('\n\n');
        buffer = messages.pop() || '';

        for (const message of messages) {
          if (!message.trim()) continue;

          const lines = message.split('\n');
          let eventType = '';
          let eventData = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7);
            } else if (line.startsWith('data: ')) {
              eventData = line.slice(6);
            }
          }

          if (!eventType || !eventData) continue;

          try {
            const parsed = JSON.parse(eventData);

            switch (eventType) {
              case 'progress':
                callbacks.onProgress(parsed as SSEProgressEvent);
                break;
              case 'complete':
                callbacks.onComplete(parsed as SSECompleteEvent);
                break;
              case 'error':
                callbacks.onError((parsed as SSEErrorEvent).message);
                break;
            }
          } catch {
            // Skip malformed events
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },
};

/**
 * Try refreshing the token and retrying the SSE request once.
 */
async function tryRefreshAndRetry(
  file: File,
  callbacks: ParseCvStreamCallbacks
): Promise<boolean> {
  const { tokens, user, setAuth, logout } = useAuthStore.getState();
  if (!tokens?.refresh_token || !user) {
    logout();
    return false;
  }

  try {
    const refreshResponse = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: tokens.refresh_token }),
    });

    if (!refreshResponse.ok) {
      logout();
      return false;
    }

    const newTokens = await refreshResponse.json();
    setAuth(user, newTokens);

    // Retry with new token
    const formData = new FormData();
    formData.append('file', file);

    const retryResponse = await fetch(
      `${API_URL}/api/v1/cv-generator/parse-stream`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${newTokens.access_token}`,
        },
        body: formData,
      }
    );

    if (!retryResponse.ok || !retryResponse.body) {
      let errorMessage = `Erreur HTTP ${retryResponse.status}`;
      try {
        const errorData = await retryResponse.json();
        errorMessage = errorData.detail || errorMessage;
      } catch {
        // Ignore
      }
      callbacks.onError(errorMessage);
      return true; // We handled it (even though it errored)
    }

    // Process the retry response stream
    const reader = retryResponse.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      let reading = true;
      while (reading) {
        const { done, value } = await reader.read();
        if (done) { reading = false; break; }

        buffer += decoder.decode(value, { stream: true });
        const messages = buffer.split('\n\n');
        buffer = messages.pop() || '';

        for (const message of messages) {
          if (!message.trim()) continue;
          const lines = message.split('\n');
          let eventType = '';
          let eventData = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) eventType = line.slice(7);
            else if (line.startsWith('data: ')) eventData = line.slice(6);
          }

          if (!eventType || !eventData) continue;

          try {
            const parsed = JSON.parse(eventData);
            switch (eventType) {
              case 'progress':
                callbacks.onProgress(parsed as SSEProgressEvent);
                break;
              case 'complete':
                callbacks.onComplete(parsed as SSECompleteEvent);
                break;
              case 'error':
                callbacks.onError((parsed as SSEErrorEvent).message);
                break;
            }
          } catch {
            // Skip malformed events
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    return true;
  } catch {
    logout();
    return false;
  }
}
