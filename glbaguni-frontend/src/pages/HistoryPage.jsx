import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useToast } from '../hooks/useToast';
import SmartLoading from '../components/SmartLoading';
import EmptyState from '../components/EmptyState';
import AccessibleButton from '../components/AccessibleButton';

const HistoryPage = () => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [languageFilter, setLanguageFilter] = useState('');

  const API_BASE_URL = import.meta.env.VITE_API_BASE;
  const { showSuccess, showError, showInfo } = useToast();

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

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);

    try {
      showInfo("히스토리를 불러오는 중...", { duration: 2000 });

      const params = {
        user_id: userId,
        page: page,
        per_page: 10
      };

      if (languageFilter) {
        params.language = languageFilter;
      }

      const response = await axios.get(`${API_BASE_URL}/history`, { params });
      setHistory(response.data.history);
      setTotalItems(response.data.total_items);

      if (response.data.history.length > 0) {
        showSuccess(`${response.data.history.length}개의 히스토리를 불러왔습니다.`);
      }
    } catch (err) {
      console.error('Failed to fetch history:', err);
      const errorMessage = '히스토리를 불러오는 중 오류가 발생했습니다.';
      setError(errorMessage);
      showError(errorMessage, {
        title: "히스토리 로드 실패",
        duration: 7000
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [page, languageFilter]);

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const truncateText = (text, maxLength = 200) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  // userId는 이제 항상 존재하므로 이 체크는 불필요

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
              📖 내 요약 히스토리
            </h1>
            <p className="text-gray-600 dark:text-gray-300">
              이전에 요약했던 기사들을 다시 확인해보세요
            </p>
          </div>

          {/* Filter Controls */}
          <div className="mb-6 flex flex-col sm:flex-row gap-4 items-center justify-between">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                언어 필터:
              </label>
              <select
                value={languageFilter}
                onChange={(e) => {
                  setLanguageFilter(e.target.value);
                  setPage(1);
                }}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              >
                <option value="">전체</option>
                <option value="ko">🇰🇷 한국어</option>
                <option value="en">🇺🇸 English</option>
              </select>
            </div>

            <AccessibleButton
              onClick={fetchHistory}
              disabled={loading}
              loading={loading}
              variant="primary"
              icon="🔄"
              ariaLabel="히스토리 새로고침"
            >
              새로고침
            </AccessibleButton>
          </div>

          {/* Loading State */}
          {loading && (
            <SmartLoading
              type="fetching"
              message="요약 히스토리를 불러오고 있습니다..."
            />
          )}

          {/* Error State */}
          {error && !loading && (
            <EmptyState
              type="error"
              customConfig={{
                icon: '😵',
                title: '히스토리를 불러올 수 없어요',
                description: error,
                action: '다시 시도',
                actionIcon: '🔄',
                onAction: fetchHistory
              }}
            />
          )}

          {/* Empty State */}
          {!loading && !error && history.length === 0 && (
            <EmptyState
              type="history"
              customConfig={{
                icon: '📚',
                title: '아직 요약 기록이 없어요',
                description: '첫 번째 요약을 시작해보세요! RSS 피드나 기사 URL을 입력하면 AI가 간결하게 요약해드립니다.',
                action: '요약 시작하기',
                actionPath: '/summarize',
                actionIcon: '✨',
                secondaryActions: [
                  { label: '뉴스 검색하기', path: '/summarize?tab=search' },
                  { label: 'RSS 추가하기', path: '/sources' }
                ],
                helpText: '요약한 모든 기사는 자동으로 히스토리에 저장되어 언제든지 다시 확인할 수 있습니다.'
              }}
            />
          )}

          {/* History Items */}
          {!loading && !error && history.length > 0 && (
            <div className="space-y-6">
              {history.map((item) => (
                <div
                  key={item.id}
                  className="bg-gray-50 dark:bg-gray-700 rounded-lg p-6 hover:shadow-md transition-shadow duration-200"
                >
                  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 sm:mb-0">
                      {item.article_title}
                    </h3>
                    <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${item.summary_language === 'ko'
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                        : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        }`}>
                        {item.summary_language === 'ko' ? '🇰🇷 한국어' : '🇺🇸 English'}
                      </span>
                      <span>{formatDate(item.created_at)}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        📄 원문 미리보기
                      </h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-800 p-3 rounded">
                        {truncateText(item.content_excerpt)}
                      </p>
                    </div>

                    <div>
                      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        ✨ AI 요약
                      </h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400 bg-white dark:bg-gray-800 p-3 rounded">
                        {truncateText(item.summary_text)}
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                      <span>📊 원문: {item.original_length}자</span>
                      <span>📝 요약: {item.summary_length}자</span>
                      {item.keywords && item.keywords.length > 0 && (
                        <span>🏷️ 키워드: {item.keywords.slice(0, 3).join(', ')}</span>
                      )}
                    </div>

                    <a
                      href={item.article_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200 text-sm font-medium"
                    >
                      🔗 원문 보기 →
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {!loading && !error && history.length > 0 && (
            <div className="mt-8 flex items-center justify-between">
              <div className="text-sm text-gray-700 dark:text-gray-300">
                총 {totalItems}개 중 {(page - 1) * 10 + 1}-{Math.min(page * 10, totalItems)}개 표시
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={page <= 1}
                  className="px-3 py-2 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-600"
                >
                  이전
                </button>

                <span className="px-3 py-2 text-sm text-gray-700 dark:text-gray-300">
                  {page} / {Math.ceil(totalItems / 10)}
                </span>

                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page >= Math.ceil(totalItems / 10)}
                  className="px-3 py-2 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-600"
                >
                  다음
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;
