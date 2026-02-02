/**
 * API Client for KarmaFeed Backend
 * 
 * Simplified auth-free version: All mutating actions use server-side demo user.
 * No CSRF, no sessions, no cookies required.
 */

const API_BASE = '/api';

/**
 * Make an API request with proper headers and error handling
 */
async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  
  const defaultHeaders = {
    'Content-Type': 'application/json',
  };
  
  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
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
 * Create a new post (uses demo user server-side)
 */
export async function createPost(title, content) {
  return apiRequest('/posts/', {
    method: 'POST',
    body: JSON.stringify({ title, content }),
  });
}

/**
 * Create a comment on a post (uses demo user server-side)
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
 * Toggle like on post or comment (uses demo user server-side)
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
