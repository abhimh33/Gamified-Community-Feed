import React, { useState, useEffect } from 'react';
import { fetchPost, toggleLike, createComment } from '../api';
import { formatDistanceToNow } from '../utils';
import Comment from './Comment';

/**
 * PostDetail Component
 * 
 * Displays full post with nested comment tree.
 * Comments are rendered recursively.
 */
function PostDetail({ postId, onBack, user }) {
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [likeLoading, setLikeLoading] = useState(false);
  const [showReplyForm, setShowReplyForm] = useState(false);
  const [replyContent, setReplyContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadPost();
  }, [postId]);

  const loadPost = async () => {
    try {
      setLoading(true);
      const data = await fetchPost(postId);
      setPost(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLikePost = async () => {
    if (!user || likeLoading) return;
    
    /**
     * OPTIMISTIC UI TRADE-OFF:
     * 
     * We're NOT using optimistic updates here. Why?
     * 
     * PROS of optimistic:
     * - Feels instant to user
     * - Better UX for slow connections
     * 
     * CONS (why we skip it):
     * - Complexity: Need to rollback on failure
     * - Race conditions: Multiple rapid clicks
     * - Consistency: UI might show wrong state
     * 
     * For a production app with high engagement,
     * optimistic UI with proper rollback would be better.
     * For this prototype, we keep it simple and correct.
     */
    
    setLikeLoading(true);
    try {
      const result = await toggleLike('post', postId);
      // Reload post to get accurate like count
      await loadPost();
    } catch (err) {
      console.error('Like failed:', err);
    } finally {
      setLikeLoading(false);
    }
  };

  const handleSubmitComment = async (e) => {
    e.preventDefault();
    if (!replyContent.trim() || submitting) return;
    
    setSubmitting(true);
    try {
      await createComment(postId, replyContent.trim());
      setReplyContent('');
      setShowReplyForm(false);
      await loadPost(); // Refresh to show new comment
    } catch (err) {
      console.error('Comment failed:', err);
    } finally {
      setSubmitting(false);
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
        <p className="font-semibold">Error loading post</p>
        <p className="text-sm mt-1">{error}</p>
        <button 
          onClick={onBack}
          className="mt-3 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-white text-sm"
        >
          Back to Feed
        </button>
      </div>
    );
  }

  if (!post) return null;

  return (
    <div className="space-y-4">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="flex items-center text-gray-400 hover:text-gray-200 transition-colors"
      >
        <span className="mr-2">←</span>
        Back to Feed
      </button>

      {/* Post */}
      <article className="bg-gray-800 rounded-lg border border-gray-700 p-6">
        {/* Post Header */}
        <div className="flex items-center text-sm text-gray-400 mb-3">
          <span className="font-medium text-gray-300">
            {post.author.username}
          </span>
          <span className="mx-2">•</span>
          <time>{formatDistanceToNow(post.created_at)}</time>
        </div>
        
        {/* Post Title */}
        <h1 className="text-2xl font-bold text-gray-100 mb-4">
          {post.title}
        </h1>
        
        {/* Post Content */}
        <div className="text-gray-300 whitespace-pre-wrap mb-6">
          {post.content}
        </div>
        
        {/* Post Actions */}
        <div className="flex items-center gap-4 pt-4 border-t border-gray-700">
          <button
            onClick={handleLikePost}
            disabled={!user || likeLoading}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              post.user_liked
                ? 'bg-red-600 text-white'
                : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <span>{post.user_liked ? '❤' : '🤍'}</span>
            <span>{post.like_count}</span>
          </button>
          
          {user && (
            <button
              onClick={() => setShowReplyForm(!showReplyForm)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-gray-300"
            >
              <span>💬</span>
              <span>Reply</span>
            </button>
          )}
          
          <span className="text-gray-400 text-sm">
            {post.comment_count} comments
          </span>
        </div>

        {/* Reply Form */}
        {showReplyForm && (
          <form onSubmit={handleSubmitComment} className="mt-4">
            <textarea
              value={replyContent}
              onChange={(e) => setReplyContent(e.target.value)}
              placeholder="Write a comment..."
              className="w-full p-3 bg-gray-700 border border-gray-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none focus:border-orange-500"
              rows={3}
            />
            <div className="flex justify-end gap-2 mt-2">
              <button
                type="button"
                onClick={() => setShowReplyForm(false)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-gray-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!replyContent.trim() || submitting}
                className="px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded text-white disabled:opacity-50"
              >
                {submitting ? 'Posting...' : 'Post Comment'}
              </button>
            </div>
          </form>
        )}
      </article>

      {/* Comments Section */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-200">
          Comments ({post.comment_count})
        </h2>
        
        {post.comments.length === 0 ? (
          <p className="text-gray-400 text-center py-8">
            No comments yet. Be the first to comment!
          </p>
        ) : (
          <div className="space-y-4">
            {post.comments.map(node => (
              <Comment
                key={node.comment.id}
                node={node}
                postId={postId}
                user={user}
                onCommentAdded={loadPost}
                depth={0}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default PostDetail;
