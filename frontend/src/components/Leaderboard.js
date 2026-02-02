import React, { useState, useEffect } from 'react';
import { fetchLeaderboard } from '../api';

/**
 * Leaderboard Component
 * 
 * Displays top 5 users by karma in last 24 hours.
 * Auto-refreshes every 60 seconds.
 */
function Leaderboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadLeaderboard = async () => {
    try {
      const result = await fetchLeaderboard(24, 5);
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLeaderboard();
    
    // Auto-refresh every 60 seconds
    const interval = setInterval(loadLeaderboard, 60000);
    return () => clearInterval(interval);
  }, []);

  const getRankEmoji = (rank) => {
    switch (rank) {
      case 1: return '🥇';
      case 2: return '🥈';
      case 3: return '🥉';
      default: return `#${rank}`;
    }
  };

  const getRankStyle = (rank) => {
    switch (rank) {
      case 1: return 'bg-gradient-to-r from-yellow-600/20 to-yellow-500/10 border-yellow-500/50';
      case 2: return 'bg-gradient-to-r from-gray-400/20 to-gray-300/10 border-gray-400/50';
      case 3: return 'bg-gradient-to-r from-orange-700/20 to-orange-600/10 border-orange-600/50';
      default: return 'bg-gray-800/50 border-gray-700';
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="bg-gray-700/50 px-4 py-3 border-b border-gray-700">
        <h2 className="font-bold text-gray-100 flex items-center gap-2">
          <span>🏆</span>
          Top Karma (24h)
        </h2>
      </div>

      {/* Content */}
      <div className="p-4">
        {loading ? (
          <div className="flex justify-center py-4">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-orange-500"></div>
          </div>
        ) : error ? (
          <div className="text-center text-gray-400 py-4">
            <p className="text-sm">{error}</p>
            <button 
              onClick={loadLeaderboard}
              className="mt-2 text-xs text-orange-500 hover:text-orange-400"
            >
              Retry
            </button>
          </div>
        ) : data?.leaderboard?.length === 0 ? (
          <p className="text-center text-gray-400 py-4 text-sm">
            No karma earned in the last 24 hours
          </p>
        ) : (
          <div className="space-y-2">
            {data?.leaderboard?.map(entry => (
              <div
                key={entry.user_id}
                className={`flex items-center justify-between p-3 rounded-lg border ${getRankStyle(entry.rank)}`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl w-8">
                    {getRankEmoji(entry.rank)}
                  </span>
                  <span className="font-medium text-gray-200">
                    {entry.username}
                  </span>
                </div>
                <div className="text-right">
                  <span className="font-bold text-orange-400">
                    {entry.total_karma}
                  </span>
                  <span className="text-gray-500 text-sm ml-1">
                    karma
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* User's Stats */}
        {data?.user_stats && (
          <div className="mt-4 pt-4 border-t border-gray-700">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">Your karma today:</span>
              <span className="font-bold text-orange-400">
                {data.user_stats.karma}
              </span>
            </div>
          </div>
        )}

        {/* Time indicator */}
        <div className="mt-4 text-center text-xs text-gray-500">
          Updates every minute
        </div>
      </div>
    </div>
  );
}

export default Leaderboard;
