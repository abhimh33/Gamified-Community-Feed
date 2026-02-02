import React, { useState, useEffect } from 'react';
import { fetchFeed } from '../api';
import PostCard from './PostCard';

/**
 * Feed Component
 * 
 * Displays paginated list of posts with infinite scroll.
 * Uses cursor-based pagination for efficiency.
 */
function Feed({ onPostClick }) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [nextCursor, setNextCursor] = useState(null);
  const [loadingMore, setLoadingMore] = useState(false);

  // Initial load
  useEffect(() => {
    loadPosts();
  }, []);

  const loadPosts = async (cursor = null) => {
    try {
      if (cursor) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }
      
      const data = await fetchFeed(cursor);
      
      if (cursor) {
        // Append to existing posts
        setPosts(prev => [...prev, ...data.results]);
      } else {
        // Replace posts
        setPosts(data.results);
      }
      
      setNextCursor(data.next ? new URL(data.next).searchParams.get('cursor') : null);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  const handleLoadMore = () => {
    if (nextCursor && !loadingMore) {
      loadPosts(nextCursor);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 text-red-200">
        <p className="font-semibold">Error loading feed</p>
        <p className="text-sm mt-1">{error}</p>
        <button 
          onClick={() => loadPosts()}
          className="mt-3 px-4 py-2 bg-red-700 hover:bg-red-600 rounded text-white text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  if (posts.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <p className="text-xl">No posts yet</p>
        <p className="text-sm mt-2">Be the first to create a post!</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {posts.map(post => (
        <PostCard 
          key={post.id} 
          post={post} 
          onClick={() => onPostClick(post.id)}
        />
      ))}
      
      {/* Load More Button */}
      {nextCursor && (
        <div className="text-center py-4">
          <button
            onClick={handleLoadMore}
            disabled={loadingMore}
            className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-gray-200 disabled:opacity-50"
          >
            {loadingMore ? 'Loading...' : 'Load More'}
          </button>
        </div>
      )}
    </div>
  );
}

export default Feed;
