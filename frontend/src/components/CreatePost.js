import React, { useState } from 'react';
import { createPost } from '../api';

/**
 * CreatePost Component
 * 
 * Modal form for creating new posts.
 * 
 * ERROR HANDLING STRATEGY:
 * - Uses try/catch but NEVER silently swallows errors
 * - Validation errors (HTTP 400): Display per-field under inputs
 * - Network/other errors: Display in general error banner
 * - Errors clear when user edits the corresponding field
 * 
 * ERROR STATE STRUCTURE:
 * {
 *   title: "Error message for title field",
 *   content: "Error message for content field"
 * }
 */
function CreatePost({ onClose, onSuccess }) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);
  
  // Field-level errors: { title: "msg", content: "msg" }
  // We flatten DRF's array format to single string for display
  const [fieldErrors, setFieldErrors] = useState({});
  
  // General error (network issues, unexpected errors)
  const [generalError, setGeneralError] = useState(null);

  /**
   * Clear error for a specific field when user starts typing
   */
  const handleTitleChange = (e) => {
    setTitle(e.target.value);
    // Clear title error immediately when user edits
    if (fieldErrors.title) {
      setFieldErrors(prev => ({ ...prev, title: null }));
    }
    if (generalError) setGeneralError(null);
  };

  const handleContentChange = (e) => {
    setContent(e.target.value);
    // Clear content error immediately when user edits
    if (fieldErrors.content) {
      setFieldErrors(prev => ({ ...prev, content: null }));
    }
    if (generalError) setGeneralError(null);
  };

  /**
   * Parse DRF validation errors into flat field error state
   * 
   * Input (DRF format): 
   *   { "title": ["Error 1", "Error 2"], "content": ["Error 3"] }
   * 
   * Output (our format):
   *   { title: "Error 1", content: "Error 3" }
   * 
   * We take only the first error per field for cleaner UI.
   */
  const parseFieldErrors = (drfErrors) => {
    const parsed = {};
    for (const [field, messages] of Object.entries(drfErrors)) {
      if (Array.isArray(messages) && messages.length > 0) {
        parsed[field] = messages[0]; // First error only
      } else if (typeof messages === 'string') {
        parsed[field] = messages;
      }
    }
    return parsed;
  };

  /**
   * SUBMIT HANDLER - Explicit error handling, no silent failures
   * 
   * Flow:
   * 1. Send POST to /api/posts/
   * 2. On success (201): Clear form, call onSuccess
   * 3. On validation error (400): Parse and display field errors
   * 4. On other error: Display general error message
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Client-side validation (quick fail)
    if (!title.trim() || !content.trim()) {
      return; // Button is disabled anyway, this is a safety check
    }
    
    setSubmitting(true);
    setFieldErrors({});
    setGeneralError(null);
    
    try {
      // Attempt to create post
      await createPost(title.trim(), content.trim());
      
      // SUCCESS: Post created (HTTP 201)
      // Clear form and notify parent
      setTitle('');
      setContent('');
      onSuccess();
      
    } catch (err) {
      // FAILURE: Handle error explicitly
      console.error('[CreatePost] Submit error:', err);
      
      // Check if this is a validation error (has fieldErrors property)
      if (err.isValidationError && err.fieldErrors) {
        // HTTP 400 - Validation error from DRF
        const parsed = parseFieldErrors(err.fieldErrors);
        setFieldErrors(parsed);
        
        // Also handle non_field_errors if present
        if (err.fieldErrors.non_field_errors) {
          const nonFieldMsg = Array.isArray(err.fieldErrors.non_field_errors)
            ? err.fieldErrors.non_field_errors[0]
            : err.fieldErrors.non_field_errors;
          setGeneralError(nonFieldMsg);
        }
      } else {
        // Network error, 500, or other unexpected error
        setGeneralError(err.message || 'An unexpected error occurred');
      }
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
        
        {/* General error banner (network issues, non_field_errors) */}
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
                {/* Title error - shown as readable text, not JSON */}
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
            {/* Content error - shown as readable text, not JSON */}
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
