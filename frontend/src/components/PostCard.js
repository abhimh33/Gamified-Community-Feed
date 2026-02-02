import React from 'react';
import { formatDistanceToNow } from '../utils';

/**
 * PostCard Component
 * 
 * Displays a post preview in the feed.
 */
function PostCard({ post, onClick }) {
  return (
    <article 
      className="bg-gray-800 rounded-lg border border-gray-700 p-4 hover:border-gray-600 cursor-pointer transition-colors"
      onClick={onClick}
    >
      {/* Post Header */}
      <div className="flex items-center text-sm text-gray-400 mb-2">
        <span className="font-medium text-gray-300">
          {post.author.username}
        </span>
        <span className="mx-2">•</span>
        <time>{formatDistanceToNow(post.created_at)}</time>
      </div>
      
      {/* Post Title */}
      <h2 className="text-xl font-semibold text-gray-100 mb-2">
        {post.title}
      </h2>
      
      {/* Post Content Preview */}
      <p className="text-gray-300 line-clamp-3 mb-3">
        {post.content}
      </p>
      
      {/* Post Stats */}
      <div className="flex items-center gap-4 text-sm text-gray-400">
        <div className="flex items-center gap-1">
          <span className="text-red-500">❤</span>
          <span>{post.like_count}</span>
        </div>
        <div className="flex items-center gap-1">
          <span>💬</span>
          <span>{post.comment_count} comments</span>
        </div>
      </div>
    </article>
  );
}

export default PostCard;
