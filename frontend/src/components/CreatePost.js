import React, { useState } from 'react';

// API base URL - same as api.js
const API_BASE = process.env.REACT_APP_API_URL || '/api';

/**
 * CreatePost Component
 * 
 * Features:
 * - Client-side validation with clear error messages
 * - Server-side validation error display
 * - Uses environment variable for API URL (production support)
 */
function CreatePost({ onClose, onSuccess }) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);
  
  // Field-level errors: { title: "msg", content: "msg" }
  const [fieldErrors, setFieldErrors] = useState({});
  
  // General error (network issues, unexpected errors)
  const [generalError, setGeneralError] = useState(null);

  // Validation constants
  const MIN_TITLE_LENGTH = 3;
  const MIN_CONTENT_LENGTH = 10;
  const MAX_TITLE_LENGTH = 300;

  /**
   * Client-side validation before submission
   */
  const validateForm = () => {
    const errors = {};
    
    if (!title.trim()) {
      errors.title = 'Title is required';
    } else if (title.trim().length < MIN_TITLE_LENGTH) {
      errors.title = `Title must be at least ${MIN_TITLE_LENGTH} characters`;
    }
    
    if (!content.trim()) {
      errors.content = 'Content is required';
    } else if (content.trim().length < MIN_CONTENT_LENGTH) {
      errors.content = `Content must be at least ${MIN_CONTENT_LENGTH} characters`;
    }
    
    return errors;
  };

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

  /**
   * SUBMIT HANDLER
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Client-side validation first
    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setFieldErrors(validationErrors);
      return;
    }
    
    setSubmitting(true);
    setFieldErrors({});
    setGeneralError(null);
    
    try {
      // Use API_BASE for production URL support
      const response = await fetch(`${API_BASE}/posts/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: title.trim(),
          content: content.trim(),
        }),
      });
      
      // Parse JSON body (ALWAYS, for both success and error)
      const data = await response.json();
      
      // Handle response based on status code
      if (response.status === 201) {
        // SUCCESS: Post created
        setTitle('');
        setContent('');
        setSubmitting(false);
        onSuccess();
      } else if (response.status === 400) {
        // VALIDATION ERROR: Parse field errors from DRF format
        const fieldData = data.details || data;
        const parsed = {};
        for (const [field, messages] of Object.entries(fieldData)) {
          if (Array.isArray(messages) && messages.length > 0) {
            parsed[field] = messages[0];
          } else if (typeof messages === 'string') {
            parsed[field] = messages;
          }
        }
        setFieldErrors(parsed);
        setSubmitting(false);
      } else {
        // OTHER ERROR: 401, 403, 404, 500, etc.
        const errorMsg = data.detail || data.error || `Server error (${response.status})`;
        setGeneralError(errorMsg);
        setSubmitting(false);
      }
    } catch (error) {
      // Network error or JSON parse error
      setGeneralError('Failed to connect to server. Please try again.');
      setSubmitting(false);
    }
  };

  // Helper to show remaining characters
  const titleRemaining = MAX_TITLE_LENGTH - title.length;
  const contentLength = content.trim().length;

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
        
        {/* General error banner */}
        {generalError && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded text-red-200 text-sm">
            {generalError}
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          {/* Title Field */}
          <div className="mb-4">
            <label className="block text-gray-300 text-sm font-medium mb-2">
              Title <span className="text-gray-500">(min {MIN_TITLE_LENGTH} characters)</span>
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
              maxLength={MAX_TITLE_LENGTH}
            />
            <div className="flex justify-between items-start mt-1">
              <div className="flex-1">
                {/* Title error rendered directly under input */}
                {fieldErrors.title && (
                  <p className="text-red-400 text-sm">{fieldErrors.title}</p>
                )}
              </div>
              <span className={`text-xs ml-2 ${titleRemaining < 20 ? 'text-orange-400' : 'text-gray-500'}`}>
                {title.length}/{MAX_TITLE_LENGTH}
              </span>
            </div>
          </div>
          
          {/* Content Field */}
          <div className="mb-4">
            <label className="block text-gray-300 text-sm font-medium mb-2">
              Content <span className="text-gray-500">(min {MIN_CONTENT_LENGTH} characters)</span>
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
            <div className="flex justify-between items-start mt-1">
              <div className="flex-1">
                {fieldErrors.content && (
                  <p className="text-red-400 text-sm">{fieldErrors.content}</p>
                )}
              </div>
              <span className={`text-xs ml-2 ${contentLength < MIN_CONTENT_LENGTH ? 'text-gray-500' : 'text-green-400'}`}>
                {contentLength} characters
              </span>
            </div>
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
              disabled={submitting}
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
