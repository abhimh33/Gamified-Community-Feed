import React, { useState } from 'react';
import { createPost } from '../api';

/**
 * CreatePost Component
 * 
 * Modal form for creating new posts.
 */
function CreatePost({ onClose, onSuccess }) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!title.trim() || !content.trim()) return;
    
    setSubmitting(true);
    setError(null);
    
    try {
      await createPost(title.trim(), content.trim());
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/70"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-gray-800 rounded-lg border border-gray-700 w-full max-w-2xl mx-4 p-6">
        <h2 className="text-xl font-bold text-gray-100 mb-4">
          Create Post
        </h2>
        
        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200 text-sm">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-gray-300 text-sm font-medium mb-2">
              Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter a title..."
              className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none focus:border-orange-500"
              maxLength={300}
            />
            <div className="text-right text-xs text-gray-500 mt-1">
              {title.length}/300
            </div>
          </div>
          
          <div className="mb-4">
            <label className="block text-gray-300 text-sm font-medium mb-2">
              Content
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Share your thoughts..."
              className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none focus:border-orange-500 resize-none"
              rows={6}
            />
          </div>
          
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-gray-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!title.trim() || !content.trim() || submitting}
              className="px-6 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? 'Creating...' : 'Create Post'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CreatePost;
