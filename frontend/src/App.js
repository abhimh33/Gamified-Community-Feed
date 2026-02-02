import React, { useState, useEffect } from 'react';
import Feed from './components/Feed';
import PostDetail from './components/PostDetail';
import Leaderboard from './components/Leaderboard';
import CreatePost from './components/CreatePost';
import AuthBar from './components/AuthBar';
import { whoAmI } from './api';

/**
 * Main App Component
 * 
 * Simple routing without react-router for prototype simplicity.
 * State:
 * - view: 'feed' | 'post'
 * - selectedPostId: number | null
 * - user: current user info
 */
function App() {
  const [view, setView] = useState('feed');
  const [selectedPostId, setSelectedPostId] = useState(null);
  const [user, setUser] = useState(null);
  const [showCreatePost, setShowCreatePost] = useState(false);

  // Check if user is logged in on mount
  useEffect(() => {
    whoAmI()
      .then(data => {
        if (data.authenticated) {
          setUser(data);
        }
      })
      .catch(console.error);
  }, []);

  const handlePostClick = (postId) => {
    setSelectedPostId(postId);
    setView('post');
  };

  const handleBackToFeed = () => {
    setSelectedPostId(null);
    setView('feed');
  };

  const handlePostCreated = () => {
    setShowCreatePost(false);
    // Trigger feed refresh by changing key
    setView('feed');
  };

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 
            className="text-2xl font-bold text-orange-500 cursor-pointer"
            onClick={handleBackToFeed}
          >
            🔥 KarmaFeed
          </h1>
          <AuthBar user={user} onUserChange={setUser} />
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Column */}
          <div className="lg:col-span-3">
            {view === 'feed' && (
              <>
                {/* Create Post Button */}
                {user && (
                  <button
                    onClick={() => setShowCreatePost(true)}
                    className="w-full mb-4 bg-orange-600 hover:bg-orange-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors"
                  >
                    + Create Post
                  </button>
                )}
                
                {/* Create Post Modal */}
                {showCreatePost && (
                  <CreatePost 
                    onClose={() => setShowCreatePost(false)}
                    onSuccess={handlePostCreated}
                  />
                )}
                
                {/* Feed */}
                <Feed onPostClick={handlePostClick} />
              </>
            )}
            
            {view === 'post' && selectedPostId && (
              <PostDetail 
                postId={selectedPostId} 
                onBack={handleBackToFeed}
                user={user}
              />
            )}
          </div>

          {/* Sidebar - Leaderboard */}
          <div className="lg:col-span-1">
            <div className="sticky top-20">
              <Leaderboard />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
