import React, { useState } from 'react';

/**
 * CreatePost Component
 * 
 * CRITICAL: This component uses DIRECT FETCH with explicit status code handling.
 * NO try/catch. NO early returns. NO error swallowing.
 * 
 * Control Flow:
 *   1. fetch() → always get response
 *   2. response.json() → always parse body
 *   3. Check status codes explicitly → always handle result
 */
function CreatePost({ onClose, onSuccess }) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);
  
  // Field-level errors: { title: "msg", content: "msg" }
  const [fieldErrors, setFieldErrors] = useState({});
  
  // General error (network issues, unexpected errors)
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

  /**
   * SUBMIT HANDLER
   * 
   * STRUCTURE (EXACTLY AS REQUIRED):
   *   const response = await fetch(...)
   *   const data = await response.json()
   *   if (response.status === 201) { success }
   *   else if (response.status === 400) { field errors }
   *   else { generic error }
   * 
   * NO try/catch. NO early returns. NO error swallowing.
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!title.trim() || !content.trim()) {
      return;
    }
    
    setSubmitting(true);
    setFieldErrors({});
    setGeneralError(null);
    
    // Step 1: Make the fetch request
    const response = await fetch('/api/posts/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        title: title.trim(),
        content: content.trim(),
      }),
    });
    
    // Step 2: Parse JSON body (ALWAYS, for both success and error)
    const data = await response.json();
    
    // Step 3: Handle response based on status code (NO EARLY RETURNS)
    if (response.status === 201) {
      // SUCCESS: Post created
      setTitle('');
      setContent('');
      setSubmitting(false);
      onSuccess();
    } else if (response.status === 400) {
      // VALIDATION ERROR: Parse field errors from DRF format
      // Backend returns: { "error": "...", "details": { "title": ["Error 1"], "content": ["Error 2"] } }
      // We extract from details and convert to: { title: "Error 1", content: "Error 2" }
      const fieldData = data.details || data; // Support both wrapped and unwrapped formats
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
                {/* Title error rendered directly under input */}
                {fieldErrors.title && (
                  <p className="text-red-400 text-sm">{fieldErrors.title}</p>
                )}
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
            {/* Content error rendered directly under textarea */}
            {fieldErrors.content && (
              <p className="text-red-400 text-sm mt-1">{fieldErrors.content}</p>
            )}
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
