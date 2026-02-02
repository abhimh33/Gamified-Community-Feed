/**
 * Utility Functions
 */

/**
 * Format a date as relative time (e.g., "5 minutes ago")
 * 
 * Simple implementation without external dependencies.
 * For production, use date-fns or similar.
 */
export function formatDistanceToNow(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);
  
  if (seconds < 60) {
    return 'just now';
  }
  
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  
  const days = Math.floor(hours / 24);
  if (days < 7) {
    return `${days}d ago`;
  }
  
  const weeks = Math.floor(days / 7);
  if (weeks < 4) {
    return `${weeks}w ago`;
  }
  
  const months = Math.floor(days / 30);
  if (months < 12) {
    return `${months}mo ago`;
  }
  
  const years = Math.floor(days / 365);
  return `${years}y ago`;
}

/**
 * Truncate text to a maximum length with ellipsis
 */
export function truncate(text, maxLength) {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

/**
 * Debounce a function
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
