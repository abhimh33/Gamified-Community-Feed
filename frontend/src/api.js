/**
 * API Client for KarmaFeed Backend
 * 
 * All API calls go through this module for:
 * 1. Consistent error handling
 * 2. CSRF token management
 * 3. Base URL configuration
 */

const API_BASE = '/api';

/**
 * Get CSRF token from cookie (Django sets this)
 */
function getCsrfToken() {
  const name = 'csrftoken';
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    const [key, value] = cookie.trim().split('=');
    if (key === name) return value;
  }
  return null;
}

/**
 * Make an API request with proper headers and error handling
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  
  const defaultHeaders = {
    'Content-Type': 'application/json',
  };
  
  // Add CSRF token for mutating requests
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      defaultHeaders['X-CSRFToken'] = csrfToken;
    }
  }
  
  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
    credentials: 'include', // Include cookies for session auth
  });
  
  // Handle non-JSON responses
  const contentType = response.headers.get('content-type');
  if (!contentType || !contentType.includes('application/json')) {
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return null;
  }
  
  const data = await response.json();
  
  if (!response.ok) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  
  return data;
}

// ============================================================================
// API ENDPOINTS
// ============================================================================

/**
 * Fetch paginated feed
 */
export async function fetchFeed(cursor = null) {
  const params = cursor ? `?cursor=${cursor}` : '';
  return apiRequest(`/feed/${params}`);
}

/**
 * Fetch single post with comments
 */
export async function fetchPost(postId) {
  return apiRequest(`/posts/${postId}/`);
}

/**
 * Create a new post
 */
export async function createPost(title, content) {
  return apiRequest('/posts/', {
    method: 'POST',
    body: JSON.stringify({ title, content }),
  });
}

/**
 * Create a comment on a post
 */
export async function createComment(postId, content, parentId = null) {
  return apiRequest(`/posts/${postId}/comments/`, {
    method: 'POST',
    body: JSON.stringify({ 
      content, 
      parent: parentId 
    }),
  });
}

/**
 * Toggle like on post or comment
 */
export async function toggleLike(targetType, targetId) {
  return apiRequest('/likes/toggle/', {
    method: 'POST',
    body: JSON.stringify({
      target_type: targetType,
      target_id: targetId,
    }),
  });
}

/**
 * Fetch leaderboard
 */
export async function fetchLeaderboard(hours = 24, limit = 5) {
  return apiRequest(`/leaderboard/?hours=${hours}&limit=${limit}`);
}

/**
 * Mock login for development
 */
export async function mockLogin(username) {
  return apiRequest('/auth/mock-login/', {
    method: 'POST',
    body: JSON.stringify({ username }),
  });
}

/**
 * Get current user info
 */
export async function whoAmI() {
  return apiRequest('/auth/whoami/');
}
