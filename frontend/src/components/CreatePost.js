import React, { useState } from 'react';
import { createPost, ApiValidationError } from '../api';

/**
 * CreatePost Component
 * 
 * Modal form for creating new posts.
 * Handles DRF validation errors with field-level display.
 */
function CreatePost({ onClose, onSuccess }) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);
  
  // Field-level errors: { title: [...], content: [...] }
  const [fieldErrors, setFieldErrors] = useState({});
  // General error (network issues, etc.)
  const [generalError, setGeneralError] = useState(null);

  /**
   * Clear error for a specific field when user starts typing
   */
  const handleTitleChange = (e) => {
    setTitle(e.target.value);
    if (fieldErrors.title) {
      setFieldErrors(prev => ({ ...prev, title: null }));
    }
    if (generalError) setGeneralError(null);
  };

  const handleContentChange = (e) => {
    setContent(e.target.value);
    if (fieldErrors.content) {
      setFieldErrors(prev => ({ ...prev, content: null }));
    }
    if (generalError) setGeneralError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!title.trim() || !content.trim()) return;
    
    setSubmitting(true);
    setFieldErrors({});
    setGeneralError(null);
    
    try {
      await createPost(title.trim(), content.trim());
      onSuccess();
    } catch (err) {
      if (err instanceof ApiValidationError) {
        // DRF validation errors - display per-field
        setFieldErrors(err.fieldErrors);
      } else {
        // Network or other errors
        setGeneralError(err.message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  /**
   * Render error messages for a field
   * DRF returns arrays: ["Error 1", "Error 2"]
   */
  const renderFieldErrors = (errors) => {
    if (!errors || errors.length === 0) return null;
    
    return (
      <div className="mt-1 space-y-1">
        {errors.map((msg, idx) => (
          <p key={idx} className="text-red-400 text-sm">
            {msg}
          </p>
        ))}
      </div>
    );
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
        
        {/* General error (network issues, etc.) */}
        {generalError && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200 text-sm">
            {generalError}
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          {/* Title Field */}
          <div className="mb-4">
            <label className="block text-gray-300 text-sm font-medium mb-2">
              Title
            </label>
            <input
              type="text"
              value={title}
              onChange={handleTitleChange}
              placeholder="Enter a title..."
              className={`w-full p-3 bg-gray-700 border rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none ${
                fieldErrors.title 
                  ? 'border-red-500 focus:border-red-500' 
                  : 'border-gray-600 focus:border-orange-500'
              }`}
              maxLength={300}
            />
            <div className="flex justify-between items-start mt-1">
              <div className="flex-1">
                {renderFieldErrors(fieldErrors.title)}
              </div>
              <span className="text-xs text-gray-500 ml-2">
                {title.length}/300
              </span>
            </div>
          </div>
          
          {/* Content Field */}
          <div className="mb-4">
            <label className="block text-gray-300 text-sm font-medium mb-2">
              Content
            </label>
            <textarea
              value={content}
              onChange={handleContentChange}
              placeholder="Share your thoughts..."
              className={`w-full p-3 bg-gray-700 border rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none resize-none ${
                fieldErrors.content 
                  ? 'border-red-500 focus:border-red-500' 
                  : 'border-gray-600 focus:border-orange-500'
              }`}
              rows={6}
            />
            {renderFieldErrors(fieldErrors.content)}
          </div>
          
          {/* Non-field errors (e.g., "non_field_errors" from DRF) */}
          {fieldErrors.non_field_errors && (
            <div className="mb-4">
              {renderFieldErrors(fieldErrors.non_field_errors)}
            </div>
          )}
          
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
