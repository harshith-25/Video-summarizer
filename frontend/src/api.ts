// export const BASE_URL = 'http://localhost:7879'; // FastAPI backend default port
export const BASE_URL = 'https://silfratech.in/video-summarizer-backend/'; // FastAPI backend default port

export function getToken(): string | null {
  return localStorage.getItem('token');
}

export function setToken(token: string | null) {
  if (token) {
    localStorage.setItem('token', token);
  } else {
    localStorage.removeItem('token');
  }
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

async function request(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Auto-detect JSON content type if body is present and not FormData
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers
  });

  if (response.status === 401) {
    // Session expired or invalid
    setToken(null);
    window.dispatchEvent(new Event('auth-status-change'));
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Authentication
  async signup(payload: any) {
    return request('/api/auth/signup', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  async login(payload: any) {
    const data = await request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    if (data.access_token) {
      setToken(data.access_token);
      window.dispatchEvent(new Event('auth-status-change'));
    }
    return data;
  },

  async getMe() {
    return request('/api/auth/me');
  },

  // Videos & Jobs
  async getVideos() {
    return request('/api/videos');
  },

  async submitUrl(url: string, title?: string, language?: string) {
    return request('/api/video/url', {
      method: 'POST',
      body: JSON.stringify({ url, title, language: language || 'en' })
    });
  },

  async uploadFile(file: File, title?: string, language?: string, onProgress?: (pct: number) => void) {
    const token = getToken();
    const formData = new FormData();
    formData.append('file', file);
    if (title) {
      formData.append('title', title);
    }
    if (language) {
      formData.append('language', language);
    }

    // Using XMLHttpRequest to get real upload progress
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${BASE_URL}/api/video/upload`);
      
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          const percentComplete = Math.round((event.loaded / event.total) * 100);
          onProgress(percentComplete);
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch (e) {
            resolve({ success: true });
          }
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            reject(new Error(err.detail || 'Upload failed'));
          } catch (e) {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        }
      };

      xhr.onerror = () => {
        reject(new Error('Network error during upload'));
      };

      xhr.send(formData);
    });
  },

  async getJobStatus(jobId: string) {
    return request(`/api/job/${jobId}/status`);
  },

  async getSummary(videoId: number) {
    return request(`/api/summary/${videoId}`);
  },

  async deleteSummary(videoId: number) {
    return request(`/api/summary/${videoId}`, {
      method: 'DELETE'
    });
  },

  async deleteJob(jobId: string) {
    return request(`/api/job/${jobId}`, {
      method: 'DELETE'
    });
  },

  // Document downloads
  async downloadFile(videoId: number, fileType: 'pdf' | 'docx' | 'md', filename: string) {
    const token = getToken();
    const response = await fetch(`${BASE_URL}/api/summary/${videoId}/download/${fileType}`, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    });

    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  }
};
