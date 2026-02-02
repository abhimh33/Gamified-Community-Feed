import React, { useState } from 'react';
import { toggleLike, createComment } from '../api';
import { formatDistanceToNow } from '../utils';

/**
 * Comment Component
 * 
 * RECURSIVE RENDERING for nested comments.
 * Auth-free demo mode: All actions always enabled.
 * 
 * Each Comment receives a 'node' with structure:
 * {
 *   comment: { id, content, author, ... },
 *   replies: [ ...more nodes... ]
 * }
 * 
 * DEPTH LIMIT:
 * We limit visual nesting to 6 levels to prevent
 * extremely narrow comment threads on mobile.
 * After depth 6, replies are shown without additional indentation.
 */
const MAX_VISUAL_DEPTH = 6;

function Comment({ node, postId, onCommentAdded, depth = 0 }) {
  const { comment, replies } = node;
  const [likeLoading, setLikeLoading] = useState(false);
  const [showReplyForm, setShowReplyForm] = useState(false);
  const [replyContent, setReplyContent] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [localLikeCount, setLocalLikeCount] = useState(comment.like_count);
  const [isLiked, setIsLiked] = useState(false);

  // Calculate indentation (capped at MAX_VISUAL_DEPTH)
  const visualDepth = Math.min(depth, MAX_VISUAL_DEPTH);
  const indentClass = visualDepth > 0 ? 'ml-4 md:ml-8' : '';
  
  // Different border colors for different depths (visual hierarchy)
  const borderColors = [
    'border-l-orange-500',
    'border-l-blue-500',
    'border-l-green-500',
    'border-l-purple-500',
    'border-l-pink-500',
    'border-l-yellow-500',
    'border-l-gray-500',
  ];
  const borderColor = borderColors[visualDepth % borderColors.length];

  const handleLike = async () => {
    if (likeLoading) return;
    
    setLikeLoading(true);
    try {
      const result = await toggleLike('comment', comment.id);
      // Update local state
      if (result.action === 'created') {
        setLocalLikeCount(prev => prev + 1);
        setIsLiked(true);
      } else if (result.action === 'removed') {
        setLocalLikeCount(prev => Math.max(0, prev - 1));
        setIsLiked(false);
      }
    } catch (err) {
      console.error('Like failed:', err);
    } finally {
      setLikeLoading(false);
    }
  };

  const handleSubmitReply = async (e) => {
    e.preventDefault();
    if (!replyContent.trim() || submitting) return;
    
    setSubmitting(true);
    try {
      await createComment(postId, replyContent.trim(), comment.id);
      setReplyContent('');
      setShowReplyForm(false);
      onCommentAdded(); // Refresh parent to show new reply
    } catch (err) {
      console.error('Reply failed:', err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={`${indentClass}`}>
      <div className={`bg-gray-800 rounded-lg border-l-4 ${borderColor} p-4`}>
        {/* Comment Header */}
        <div className="flex items-center text-sm text-gray-400 mb-2">
          <span className="font-medium text-gray-300">
            {comment.author.username}
          </span>
          <span className="mx-2">•</span>
          <time>{formatDistanceToNow(comment.created_at)}</time>
          {comment.depth > 0 && (
            <span className="ml-2 text-xs text-gray-500">
              (depth {comment.depth})
            </span>
          )}
        </div>
        
        {/* Comment Content */}
        <p className="text-gray-200 whitespace-pre-wrap mb-3">
          {comment.content}
        </p>
        
        {/* Comment Actions */}
        <div className="flex items-center gap-3 text-sm">
          <button
            onClick={handleLike}
            disabled={likeLoading}
            className={`flex items-center gap-1 px-2 py-1 rounded transition-colors ${
              isLiked
                ? 'text-red-400'
                : 'text-gray-400 hover:text-red-400'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <span>{isLiked ? '❤' : '🤍'}</span>
            <span>{localLikeCount}</span>
          </button>
          
          <button
            onClick={() => setShowReplyForm(!showReplyForm)}
            className="text-gray-400 hover:text-gray-200 transition-colors"
          >
            Reply
          </button>
        </div>

        {/* Reply Form */}
        {showReplyForm && (
          <form onSubmit={handleSubmitReply} className="mt-3">
            <textarea
              value={replyContent}
              onChange={(e) => setReplyContent(e.target.value)}
              placeholder="Write a reply..."
              className="w-full p-2 bg-gray-700 border border-gray-600 rounded text-gray-100 placeholder-gray-400 focus:outline-none focus:border-orange-500 text-sm"
              rows={2}
            />
            <div className="flex justify-end gap-2 mt-2">
              <button
                type="button"
                onClick={() => setShowReplyForm(false)}
                className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded text-gray-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!replyContent.trim() || submitting}
                className="px-3 py-1 text-sm bg-orange-600 hover:bg-orange-700 rounded text-white disabled:opacity-50"
              >
                {submitting ? 'Posting...' : 'Reply'}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Nested Replies - RECURSIVE */}
      {replies && replies.length > 0 && (
        <div className="mt-2 space-y-2">
          {replies.map(replyNode => (
            <Comment
              key={replyNode.comment.id}
              node={replyNode}
              postId={postId}
              onCommentAdded={onCommentAdded}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default Comment;
