import React, { useState, useEffect } from 'react';
import { sourcesAPI, authAPI } from '../utils/api';

const SourcesPage = () => {
  // State management
  const [sources, setSources] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('cards'); // 'cards' or 'select'
  const [currentUser, setCurrentUser] = useState(null);
  const [subscribingSource, setSubscribingSource] = useState(null);
  const [subscribeMessage, setSubscribeMessage] = useState('');

  // Load data when component mounts
  useEffect(() => {
    loadInitialData();
    loadCurrentUser();
  }, []);

  // Reload sources when category changes
  useEffect(() => {
    if (selectedCategory) {
      loadSourcesByCategory(selectedCategory);
    } else {
      loadAllSources();
    }
  }, [selectedCategory]);

  // Load initial data
  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load data in parallel
      const [sourcesResponse, categoriesResponse] = await Promise.all([
        sourcesAPI.getAllSources(),
        sourcesAPI.getCategories()
      ]);

      if (sourcesResponse.success) {
        setSources(sourcesResponse.sources);
      } else {
        throw new Error(sourcesResponse.message);
      }

      if (categoriesResponse.success) {
        setCategories(categoriesResponse.categories);
      }

    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Failed to load data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Load all sources
  const loadAllSources = async () => {
    try {
      setLoading(true);
      const response = await sourcesAPI.getAllSources();
      
      if (response.success) {
        setSources(response.sources);
      } else {
        throw new Error(response.message);
      }
    } catch (err) {
      console.error('Failed to load all sources:', err);
      setError('Failed to load sources: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Load current user info
  const loadCurrentUser = async () => {
    try {
      const response = await authAPI.getCurrentUser();
      setCurrentUser(response);
    } catch (err) {
      console.error('Failed to load current user:', err);
      // User might not be logged in, that's okay
    }
  };

  // Load sources by category
  const loadSourcesByCategory = async (category) => {
    try {
      setLoading(true);
      const response = await sourcesAPI.getSourcesByCategory(category);
      
      if (response.success) {
        setSources(response.sources);
      } else {
        throw new Error(response.message);
      }
    } catch (err) {
      console.error('Failed to load sources by category:', err);
      setError('Failed to load sources: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Category change handler
  const handleCategoryChange = (e) => {
    setSelectedCategory(e.target.value);
  };

  // View mode change handler
  const handleViewModeChange = (mode) => {
    setViewMode(mode);
  };

  // Handle source subscription
  const handleSubscribe = async (source) => {
    if (!currentUser) {
      setSubscribeMessage('로그인이 필요합니다.');
      return;
    }

    try {
      setSubscribingSource(source.rss_url);
      setSubscribeMessage('');

      const response = await sourcesAPI.subscribe(
        currentUser.id,
        source.name,
        source.rss_url
      );

      if (response.success) {
        setSubscribeMessage(`'${source.name}' 구독이 완료되었습니다.`);
      } else {
        setSubscribeMessage(response.message || '구독에 실패했습니다.');
      }
    } catch (err) {
      console.error('Subscription failed:', err);
      setSubscribeMessage(err.response?.data?.message || '구독에 실패했습니다.');
    } finally {
      setSubscribingSource(null);
      // Clear message after 3 seconds
      setTimeout(() => setSubscribeMessage(''), 3000);
    }
  };

  // Category color mapping
  const getCategoryColor = (category) => {
    const colors = {
      '종합': 'bg-blue-100 text-blue-800',
      'IT': 'bg-green-100 text-green-800',
      '통신': 'bg-purple-100 text-purple-800',
      '경제': 'bg-yellow-100 text-yellow-800',
      '방송': 'bg-red-100 text-red-800',
    };
    return colors[category] || 'bg-gray-100 text-gray-800';
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading news sources...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="text-red-600 text-xl mb-4">⚠️ Error</div>
            <p className="text-gray-600">{error}</p>
            <button
              onClick={loadInitialData}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">News Sources</h1>
          <p className="text-gray-600">Explore various news sources from different media outlets</p>
          
          {/* Subscription message */}
          {subscribeMessage && (
            <div className={`mt-4 p-3 rounded-md ${
              subscribeMessage.includes('완료') || subscribeMessage.includes('success') 
                ? 'bg-green-100 text-green-800' 
                : 'bg-red-100 text-red-800'
            }`}>
              {subscribeMessage}
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
          {/* Category filter */}
          <div className="flex items-center space-x-4">
            <label htmlFor="category" className="text-sm font-medium text-gray-700">
              Category:
            </label>
            <select
              id="category"
              value={selectedCategory}
              onChange={handleCategoryChange}
              className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All</option>
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </div>

          {/* View mode toggle */}
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-gray-700">View:</span>
            <div className="flex rounded-lg border border-gray-300 overflow-hidden">
              <button
                onClick={() => handleViewModeChange('cards')}
                className={`px-4 py-2 text-sm font-medium ${
                  viewMode === 'cards'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                } transition-colors`}
              >
                Cards
              </button>
              <button
                onClick={() => handleViewModeChange('select')}
                className={`px-4 py-2 text-sm font-medium ${
                  viewMode === 'select'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-50'
                } transition-colors`}
              >
                List
              </button>
            </div>
          </div>
        </div>

        {/* Results counter */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-gray-600">
            Total <span className="font-semibold text-blue-600">{sources.length}</span> news sources
            {selectedCategory && (
              <span> (Category: <span className="font-semibold">{selectedCategory}</span>)</span>
            )}
          </p>
          
          {/* User status */}
          <div className="text-sm text-gray-600 mt-2 sm:mt-0">
            {currentUser ? (
              <span className="text-green-600">
                👤 {currentUser.username} (로그인됨)
              </span>
            ) : (
              <span className="text-red-600">
                ⚠️ 구독하려면 로그인이 필요합니다
              </span>
            )}
          </div>
        </div>

        {/* Card view */}
        {viewMode === 'cards' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {sources.map((source, index) => (
              <div
                key={index}
                className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 p-6"
              >
                <div className="flex items-start justify-between mb-3">
                  <h3 className="text-lg font-semibold text-gray-900 flex-1">
                    {source.name}
                  </h3>
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(
                      source.category
                    )}`}
                  >
                    {source.category}
                  </span>
                </div>
                
                <div className="space-y-2">
                  <div className="text-sm text-gray-600">
                    <span className="font-medium">RSS URL:</span>
                  </div>
                  <div className="bg-gray-50 p-2 rounded border">
                    <code className="text-xs text-gray-800 break-all">
                      {source.rss_url}
                    </code>
                  </div>
                </div>
                
                <div className="mt-4 flex space-x-2">
                  <button
                    onClick={() => handleSubscribe(source)}
                    disabled={subscribingSource === source.rss_url}
                    className={`flex-1 px-3 py-2 text-sm font-medium rounded-md transition-colors text-center ${
                      subscribingSource === source.rss_url
                        ? 'bg-gray-400 text-white cursor-not-allowed'
                        : currentUser
                        ? 'bg-green-600 text-white hover:bg-green-700'
                        : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    }`}
                    title={!currentUser ? '로그인이 필요합니다' : '구독하기'}
                  >
                    {subscribingSource === source.rss_url ? '구독 중...' : '구독하기'}
                  </button>
                  <a
                    href={source.rss_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
                    title="RSS 보기"
                  >
                    📡
                  </a>
                  <button
                    onClick={() => navigator.clipboard.writeText(source.rss_url)}
                    className="px-3 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-200 transition-colors"
                    title="URL 복사"
                  >
                    📋
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Select box view */}
        {viewMode === 'select' && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="mb-4">
              <label htmlFor="source-select" className="block text-sm font-medium text-gray-700 mb-2">
                Select News Source:
              </label>
              <select
                id="source-select"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                defaultValue=""
              >
                <option value="" disabled>
                  Choose a news source ({sources.length} available)
                </option>
                {sources.map((source, index) => (
                  <option key={index} value={source.rss_url}>
                    [{source.category}] {source.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Table view */}
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Media Outlet
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Category
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      RSS URL
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {sources.map((source, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {source.name}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getCategoryColor(
                            source.category
                          )}`}
                        >
                          {source.category}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900 break-all max-w-xs">
                          <code className="bg-gray-100 px-1 py-0.5 rounded text-xs">
                            {source.rss_url}
                          </code>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                        <button
                          onClick={() => handleSubscribe(source)}
                          disabled={subscribingSource === source.rss_url}
                          className={`${
                            subscribingSource === source.rss_url
                              ? 'text-gray-400 cursor-not-allowed'
                              : currentUser
                              ? 'text-green-600 hover:text-green-900'
                              : 'text-gray-400 cursor-not-allowed'
                          }`}
                          title={!currentUser ? '로그인이 필요합니다' : '구독하기'}
                        >
                          {subscribingSource === source.rss_url ? '구독중...' : '구독'}
                        </button>
                        <a
                          href={source.rss_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-900"
                        >
                          보기
                        </a>
                        <button
                          onClick={() => navigator.clipboard.writeText(source.rss_url)}
                          className="text-gray-600 hover:text-gray-900"
                          title="URL 복사"
                        >
                          복사
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Empty state */}
        {sources.length === 0 && !loading && (
          <div className="text-center py-12">
            <div className="text-gray-400 text-6xl mb-4">📰</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No news sources found
            </h3>
            <p className="text-gray-600">
              {selectedCategory
                ? `No news sources found for '${selectedCategory}' category.`
                : 'No news sources are currently available.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SourcesPage; 