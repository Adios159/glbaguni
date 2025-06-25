import React, { useState, useEffect } from 'react';
import axios from 'axios';

const RecommendationPage = () => {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [maxRecommendations, setMaxRecommendations] = useState(10);

  const API_BASE_URL = import.meta.env.VITE_API_BASE;
  
  // 사용자 ID 가져오기 또는 생성
  const getUserId = () => {
    let userId = localStorage.getItem('user_id');
    if (!userId) {
      userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('user_id', userId);
    }
    return userId;
  };
  
  const userId = getUserId();

  const fetchRecommendations = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/recommendations`, {
        params: {
          user_id: userId,
          max_recommendations: maxRecommendations
        }
      });
      setRecommendations(response.data.recommendations);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch recommendations:', err);
      setError('추천 기사를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, [maxRecommendations]);

  const logClick = async (articleUrl) => {
    try {
      await axios.post(`${API_BASE_URL}/recommendation-click`, null, {
        params: {
          user_id: userId,
          article_url: articleUrl
        }
      });
    } catch (err) {
      console.error('Failed to log click:', err);
    }
  };

  const handleArticleClick = (articleUrl) => {
    logClick(articleUrl);
    window.open(articleUrl, '_blank', 'noopener,noreferrer');
  };

  const getRecommendationTypeLabel = (type) => {
    const typeMap = {
      'keyword': '🏷️ 키워드 기반',
      'category': '📂 카테고리 기반',
      'trending': '🔥 트렌딩'
    };
    return typeMap[type] || type;
  };

  const getRecommendationTypeColor = (type) => {
    const colorMap = {
      'keyword': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      'category': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      'trending': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    };
    return colorMap[type] || 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
              🔥 개인화된 뉴스 추천
            </h1>
            <p className="text-gray-600 dark:text-gray-300">
              당신의 관심사를 바탕으로 엄선된 뉴스를 추천해드립니다
            </p>
          </div>

          {/* Controls */}
          <div className="mb-6 flex flex-col sm:flex-row gap-4 items-center justify-between">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                추천 개수:
              </label>
              <select
                value={maxRecommendations}
                onChange={(e) => setMaxRecommendations(parseInt(e.target.value))}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              >
                <option value={5}>5개</option>
                <option value={10}>10개</option>
                <option value={15}>15개</option>
                <option value={20}>20개</option>
              </select>
            </div>
            
            <button
              onClick={fetchRecommendations}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors duration-200"
            >
              🔄 새로고침
            </button>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600 dark:text-gray-300">추천 기사를 생성하는 중...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
              <p className="text-red-700 dark:text-red-300">{error}</p>
            </div>
          )}

          {/* Empty State */}
          {!loading && !error && recommendations.length === 0 && (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">🤖</div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                추천할 기사가 없습니다
              </h3>
              <p className="text-gray-600 dark:text-gray-300 mb-6">
                더 많은 기사를 요약하시면 개인화된 추천을 받으실 수 있습니다.
              </p>
              <a
                href="/summarize"
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition-colors duration-200"
              >
                📝 더 많은 기사 요약하기
              </a>
            </div>
          )}

          {/* Recommendations */}
          {!loading && !error && recommendations.length > 0 && (
            <div className="space-y-6">
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  📊 추천 유형별 분류
                </h2>
                <div className="flex flex-wrap gap-2">
                  {[...new Set(recommendations.map(r => r.recommendation_type))].map(type => (
                    <span
                      key={type}
                      className={`px-3 py-1 rounded-full text-sm font-medium ${getRecommendationTypeColor(type)}`}
                    >
                      {getRecommendationTypeLabel(type)} ({recommendations.filter(r => r.recommendation_type === type).length})
                    </span>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {recommendations.map((item, index) => (
                  <div
                    key={index}
                    className="bg-gray-50 dark:bg-gray-700 rounded-lg p-6 hover:shadow-md transition-shadow duration-200 border-l-4 border-blue-500"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRecommendationTypeColor(item.recommendation_type)}`}>
                        {getRecommendationTypeLabel(item.recommendation_type)}
                      </span>
                      <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
                        <span className="mr-1">⭐</span>
                        <span>{(item.recommendation_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>

                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3 line-clamp-2">
                      {item.article_title}
                    </h3>

                    <div className="mb-4">
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                        🌐 출처: {item.article_source}
                      </p>
                      
                      {item.keywords && item.keywords.length > 0 && (
                        <div className="mb-2">
                          <span className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">🏷️ 관련 키워드:</span>
                          <div className="flex flex-wrap gap-1">
                            {item.keywords.slice(0, 5).map((keyword, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-1 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 text-xs rounded"
                              >
                                {keyword}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {item.category && (
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          📂 카테고리: {item.category}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-400">
                        추천 점수: {(item.recommendation_score * 100).toFixed(1)}%
                      </div>
                      
                      <button
                        onClick={() => handleArticleClick(item.article_url)}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium transition-colors duration-200"
                      >
                        📖 기사 읽기
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Info Section */}
          {!loading && recommendations.length > 0 && (
            <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-blue-800 dark:text-blue-200 mb-2">
                💡 추천 알고리즘 정보
              </h3>
              <div className="text-sm text-blue-700 dark:text-blue-300">
                <p className="mb-2">• <strong>키워드 기반:</strong> 이전에 요약한 기사들의 키워드를 분석하여 유사한 주제의 기사를 추천합니다.</p>
                <p className="mb-2">• <strong>카테고리 기반:</strong> 자주 요약하는 카테고리의 최신 기사를 추천합니다.</p>
                <p>• <strong>트렌딩:</strong> 현재 가장 인기 있는 기사들을 추천합니다.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RecommendationPage;
