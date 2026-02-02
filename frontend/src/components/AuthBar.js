import React, { useState } from 'react';
import { mockLogin } from '../api';

/**
 * AuthBar Component
 * 
 * Simple authentication UI for development.
 * Uses mock login endpoint for testing.
 */
function AuthBar({ user, onUserChange }) {
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [showLogin, setShowLogin] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!username.trim() || loading) return;
    
    setLoading(true);
    try {
      const data = await mockLogin(username.trim());
      onUserChange({
        authenticated: true,
        user_id: data.user_id,
        username: data.username
      });
      setShowLogin(false);
      setUsername('');
    } catch (err) {
      console.error('Login failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    // Clear session by refreshing (simple approach)
    document.cookie = 'sessionid=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    onUserChange(null);
  };

  if (user) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-gray-300">
          <span className="text-gray-500">Logged in as</span>{' '}
          <span className="font-medium">{user.username}</span>
        </span>
        <button
          onClick={handleLogout}
          className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded text-gray-300"
        >
          Logout
        </button>
      </div>
    );
  }

  if (showLogin) {
    return (
      <form onSubmit={handleLogin} className="flex items-center gap-2">
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Username"
          className="px-3 py-1 bg-gray-700 border border-gray-600 rounded text-gray-100 text-sm focus:outline-none focus:border-orange-500"
        />
        <button
          type="submit"
          disabled={!username.trim() || loading}
          className="px-3 py-1 text-sm bg-orange-600 hover:bg-orange-700 rounded text-white disabled:opacity-50"
        >
          {loading ? '...' : 'Login'}
        </button>
        <button
          type="button"
          onClick={() => setShowLogin(false)}
          className="px-3 py-1 text-sm text-gray-400 hover:text-gray-200"
        >
          Cancel
        </button>
      </form>
    );
  }

  return (
    <button
      onClick={() => setShowLogin(true)}
      className="px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg text-white font-medium"
    >
      Login
    </button>
  );
}

export default AuthBar;
