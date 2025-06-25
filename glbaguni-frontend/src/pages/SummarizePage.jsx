import React, { useState, useEffect } from "react";
import axios from "axios";
import { useFormValidation } from "../hooks/useFormValidation";
import { useToast } from "../hooks/useToast";
import SmartLoading from "../components/SmartLoading";
import EmptyState from "../components/EmptyState";
import AccessibleButton from "../components/AccessibleButton";

const SummarizePage = () => {
  const [activeTab, setActiveTab] = useState("search");
  const [healthStatus, setHealthStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingType, setLoadingType] = useState('fetching');

  const [formData, setFormData] = useState({
    rssUrls: "",
    articleUrls: "",
    recipientEmail: "",
    customPrompt: "",
    maxArticles: 10,
    language: "ko"
  });

  const [newsSearchData, setNewsSearchData] = useState({
    query: "",
    maxArticles: 10,
    language: "ko",
    recipientEmail: ""
  });

  const [summary, setSummary] = useState(null);
  const [newsResults, setNewsResults] = useState(null);
  const [error, setError] = useState(null);

  // 평가 관련 state 추가
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(new Set());
  const [feedbackLoading, setFeedbackLoading] = useState(false);

  const { validateForm, validationErrors } = useFormValidation();
  const { showSuccess, showError, showWarning, showInfo } = useToast();
  const API_BASE_URL = import.meta.env.VITE_API_BASE;

  useEffect(() => {
    if (!localStorage.getItem("user_id")) {
      localStorage.setItem("user_id", crypto.randomUUID());
    }
  }, []);

  const checkBackendHealth = async () => {
    setIsCheckingHealth(true);
    try {
      showInfo("백엔드 서버 연결 확인 중...", { duration: 2000 });
      const response = await axios.get(`${API_BASE_URL}/health`);
      setHealthStatus(response.data);
      setError(null);
      showSuccess("서버 연결 성공! 모든 서비스가 정상 작동 중입니다.", { duration: 3000 });
    } catch (err) {
      console.error("Health check failed:", err);
      setHealthStatus(null);
      const errorMessage = "백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.";
      setError(errorMessage);
      showError(errorMessage, {
        title: "서버 연결 실패",
        duration: 0 // 수동으로 닫을 때까지 유지
      });
    } finally {
      setIsCheckingHealth(false);
    }
  };

  useEffect(() => {
    checkBackendHealth();
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    if (activeTab === "rss") {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    } else {
      setNewsSearchData(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };

  const handleNewsSearch = async (e) => {
    e.preventDefault();

    if (!newsSearchData.query.trim()) {
      showWarning("검색어를 입력해주세요.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setNewsResults(null);
    setLoadingType('searching');
    setLoadingProgress(0);

    try {
      // 진행률 시뮬레이션
      const progressInterval = setInterval(() => {
        setLoadingProgress(prev => {
          if (prev >= 0.9) return prev;
          return prev + 0.1;
        });
      }, 1000);

      const requestData = {
        query: newsSearchData.query,
        max_articles: parseInt(newsSearchData.maxArticles),
        language: newsSearchData.language,
        recipient_email: newsSearchData.recipientEmail || null,
        user_id: localStorage.getItem("user_id")
      };

      showInfo(`"${newsSearchData.query}" 관련 뉴스를 검색하고 있습니다...`);

      const response = await axios.post(`${API_BASE_URL}/news-search`, requestData, {
        headers: {
          "Content-Type": "application/json",
        },
        timeout: 300000
      });

      clearInterval(progressInterval);
      setLoadingProgress(1);

      setTimeout(() => {
        setNewsResults(response.data);
        showSuccess(`${response.data.articles?.length || 0}개의 뉴스를 찾았습니다!`, {
          title: "검색 완료"
        });
      }, 500);

    } catch (err) {
      console.error("Error:", err);
      let errorMessage = "뉴스 검색 중 오류가 발생했습니다.";

      if (err.response) {
        errorMessage = `서버 오류: ${err.response.status} - ${err.response.data.detail || "알 수 없는 오류"}`;
      } else if (err.request) {
        errorMessage = "서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.";
      } else {
        errorMessage = `요청 처리 중 오류가 발생했습니다: ${err.message}`;
      }

      setError(errorMessage);
      showError(errorMessage, {
        title: "검색 실패",
        duration: 7000
      });
    } finally {
      setIsLoading(false);
      setLoadingProgress(0);
    }
  };

  const handleRSSSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm(formData)) {
      showWarning("입력 정보를 확인해주세요.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setSummary(null);
    setLoadingType('summarizing');
    setLoadingProgress(0);

    try {
      // 진행률 시뮬레이션
      const progressInterval = setInterval(() => {
        setLoadingProgress(prev => {
          if (prev >= 0.9) return prev;
          return prev + 0.05;
        });
      }, 2000);

      const requestData = {
        rss_urls: formData.rssUrls ? formData.rssUrls.split("\n").filter(url => url.trim()) : null,
        article_urls: formData.articleUrls ? formData.articleUrls.split("\n").filter(url => url.trim()) : null,
        recipient_email: formData.recipientEmail,
        custom_prompt: formData.customPrompt || null,
        max_articles: parseInt(formData.maxArticles),
        language: formData.language,
        user_id: localStorage.getItem("user_id")
      };

      showInfo("RSS 피드에서 기사를 수집하고 AI 요약을 진행하고 있습니다...");

      const response = await axios.post(`${API_BASE_URL}/summarize`, requestData, {
        headers: {
          "Content-Type": "application/json",
        },
        timeout: 300000
      });

      clearInterval(progressInterval);
      setLoadingProgress(1);

      setTimeout(() => {
        setSummary(response.data);
        showSuccess("요약이 완료되었습니다!", {
          title: "AI 요약 완료"
        });

        // 이메일 발송 완료 알림
        if (formData.recipientEmail && response.data.email_sent) {
          showSuccess(`${formData.recipientEmail}로 요약 결과를 발송했습니다.`, {
            title: "이메일 발송 완료"
          });
        }
      }, 500);

    } catch (err) {
      console.error("Error:", err);
      let errorMessage = "요약 생성 중 오류가 발생했습니다.";

      if (err.response) {
        errorMessage = `서버 오류: ${err.response.status} - ${err.response.data.detail || "알 수 없는 오류"}`;
      } else if (err.request) {
        errorMessage = "서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.";
      } else {
        errorMessage = `요청 처리 중 오류가 발생했습니다: ${err.message}`;
      }

      setError(errorMessage);
      showError(errorMessage, {
        title: "요약 실패",
        duration: 7000
      });
    } finally {
      setIsLoading(false);
      setLoadingProgress(0);
    }
  };

  // 피드백 제출 함수
  const submitFeedback = async (articleTitle, articleUrl, feedbackType) => {
    setFeedbackLoading(true);

    try {
      const requestData = {
        user_id: localStorage.getItem("user_id"),
        article_url: articleUrl,
        article_title: articleTitle,
        feedback_type: feedbackType,
        rating: feedbackType === "positive" ? 5 : 1, // 간단한 평점 매핑
        summary_language: activeTab === "search" ? newsSearchData.language : formData.language
      };

      const response = await axios.post(`${API_BASE_URL}/feedback`, requestData, {
        headers: {
          "Content-Type": "application/json",
        },
        timeout: 10000
      });

      if (response.data.success) {
        // 피드백 제출 완료 표시
        setFeedbackSubmitted(prev => new Set([...prev, articleUrl]));

        // 토스트로 성공 메시지 표시
        showSuccess("피드백이 성공적으로 제출되었습니다. 감사합니다! 🎉", {
          title: "피드백 완료"
        });
        setError(null);
      }
    } catch (err) {
      console.error("Feedback submission failed:", err);
      const errorMessage = "피드백 제출 중 오류가 발생했습니다. 다시 시도해주세요.";
      setError(errorMessage);
      showError(errorMessage, {
        title: "피드백 실패"
      });
    } finally {
      setFeedbackLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
              📰 뉴스 요약 서비스
            </h1>
            <p className="text-gray-600 dark:text-gray-300">
              자연어 검색이나 RSS 피드로 뉴스를 찾고 AI 요약을 받아보세요
            </p>
          </div>

          <div className="mb-6 p-4 rounded-lg bg-gray-50 dark:bg-gray-700">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                백엔드 서버 상태:
              </span>
              <div className="flex items-center space-x-2">
                {isCheckingHealth ? (
                  <span className="text-yellow-600 dark:text-yellow-400">확인 중...</span>
                ) : healthStatus ? (
                  <span className="text-green-600 dark:text-green-400">✅ 연결됨</span>
                ) : (
                  <span className="text-red-600 dark:text-red-400">❌ 연결 실패</span>
                )}
                <button
                  onClick={checkBackendHealth}
                  className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200 text-sm"
                  disabled={isCheckingHealth}
                >
                  새로고침
                </button>
              </div>
            </div>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-red-700 dark:text-red-300">{error}</p>
            </div>
          )}

          <div className="mb-6">
            <div className="border-b border-gray-200 dark:border-gray-700">
              <nav className="-mb-px flex space-x-8">
                <button
                  onClick={() => setActiveTab("search")}
                  className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === "search"
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300"
                    }`}
                >
                  🔍 자연어 뉴스 검색
                </button>
                <button
                  onClick={() => setActiveTab("rss")}
                  className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === "rss"
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300"
                    }`}
                >
                  📡 RSS & URL 요약
                </button>
              </nav>
            </div>
          </div>

          {activeTab === "search" && (
            <form onSubmit={handleNewsSearch} className="space-y-6">
              <div>
                <label htmlFor="search-query" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  🔍 뉴스 검색어 *
                </label>
                <input
                  type="text"
                  id="search-query"
                  name="query"
                  value={newsSearchData.query}
                  onChange={handleInputChange}
                  autoComplete="off"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="예: 요즘 반도체 뉴스 알려줘, 코로나 최신 소식, 주식 시장 동향"
                  required
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  자연어로 원하는 뉴스 주제를 입력하세요. AI가 키워드를 추출하여 관련 뉴스를 찾아드립니다.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="search-language" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    요약 언어
                  </label>
                  <select
                    id="search-language"
                    name="language"
                    value={newsSearchData.language}
                    onChange={handleInputChange}
                    autoComplete="language"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="ko">🇰🇷 한국어</option>
                    <option value="en">🇺🇸 English</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="search-max-articles" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    최대 기사 수
                  </label>
                  <input
                    type="number"
                    id="search-max-articles"
                    name="maxArticles"
                    value={newsSearchData.maxArticles}
                    onChange={handleInputChange}
                    min="1"
                    max="20"
                    autoComplete="off"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="search-email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  이메일 주소 (선택사항)
                </label>
                <input
                  type="email"
                  id="search-email"
                  name="recipientEmail"
                  value={newsSearchData.recipientEmail}
                  onChange={handleInputChange}
                  autoComplete="email"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="결과를 이메일로도 받고 싶다면 입력하세요"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading || !healthStatus}
                className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-bold py-3 px-4 rounded-lg transition-colors duration-200"
              >
                {isLoading ? "뉴스 검색 중..." : "🔍 뉴스 검색 시작"}
              </button>
            </form>
          )}

          {activeTab === "rss" && (
            <form onSubmit={handleRSSSubmit} className="space-y-6">
              <div>
                <label htmlFor="rss-urls" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  RSS 피드 URL (선택사항)
                </label>
                <textarea
                  id="rss-urls"
                  name="rssUrls"
                  rows="3"
                  value={formData.rssUrls}
                  onChange={handleInputChange}
                  autoComplete="off"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="https://feeds.bbci.co.uk/news/rss.xml&#10;각 URL을 새 줄에 입력하세요"
                />
              </div>

              <div>
                <label htmlFor="article-urls" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  개별 기사 URL (선택사항)
                </label>
                <textarea
                  id="article-urls"
                  name="articleUrls"
                  rows="3"
                  value={formData.articleUrls}
                  onChange={handleInputChange}
                  autoComplete="off"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="https://example.com/article1&#10;각 URL을 새 줄에 입력하세요"
                />
              </div>

              <div>
                <label htmlFor="rss-email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  이메일 주소 *
                </label>
                <input
                  type="email"
                  id="rss-email"
                  name="recipientEmail"
                  value={formData.recipientEmail}
                  onChange={handleInputChange}
                  autoComplete="email"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="your@email.com"
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="rss-language" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    요약 언어
                  </label>
                  <select
                    id="rss-language"
                    name="language"
                    value={formData.language}
                    onChange={handleInputChange}
                    autoComplete="language"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="ko">🇰🇷 한국어</option>
                    <option value="en">🇺🇸 English</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="rss-max-articles" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    최대 기사 수
                  </label>
                  <input
                    type="number"
                    id="rss-max-articles"
                    name="maxArticles"
                    value={formData.maxArticles}
                    onChange={handleInputChange}
                    min="1"
                    max="50"
                    autoComplete="off"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="custom-prompt" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  사용자 정의 프롬프트 (선택사항)
                </label>
                <textarea
                  id="custom-prompt"
                  name="customPrompt"
                  rows="3"
                  value={formData.customPrompt}
                  onChange={handleInputChange}
                  autoComplete="off"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="특별한 요약 스타일이나 포커스할 내용이 있다면 입력하세요..."
                />
              </div>

              <button
                type="submit"
                disabled={isLoading || !healthStatus}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-bold py-3 px-4 rounded-lg transition-colors duration-200"
              >
                {isLoading ? "요약 중..." : "📄 요약 시작"}
              </button>
            </form>
          )}

          {newsResults && (
            <div className="mt-8 p-6 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
              <h3 className="text-lg font-semibold text-green-800 dark:text-green-200 mb-4">
                🔍 뉴스 검색 완료!
              </h3>
              <div className="space-y-4">
                <div className="flex items-center space-x-2 text-green-700 dark:text-green-300">
                  <span>📊 총 <strong>{newsResults.total_articles}</strong>개의 관련 뉴스를 찾았습니다.</span>
                </div>
                {newsResults.extracted_keywords && newsResults.extracted_keywords.length > 0 && (
                  <div className="text-green-700 dark:text-green-300">
                    <span>🔑 추출된 키워드: </span>
                    <span className="font-medium">{newsResults.extracted_keywords.join(', ')}</span>
                  </div>
                )}
                {newsSearchData.recipientEmail && (
                  <div className="text-green-700 dark:text-green-300">
                    📧 이메일이 <strong>{newsSearchData.recipientEmail}</strong>로 발송되었습니다.
                  </div>
                )}
              </div>

              {newsResults.articles && newsResults.articles.length > 0 && (
                <div className="mt-6">
                  <h4 className="text-md font-medium text-green-800 dark:text-green-200 mb-3">
                    📰 검색된 뉴스 목록:
                  </h4>
                  <div className="space-y-4 max-h-96 overflow-y-auto">
                    {newsResults.articles.map((article, index) => (
                      <div key={index} className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow border border-green-200 dark:border-green-700">
                        <h5 className="font-medium text-gray-900 dark:text-white mb-2">
                          {index + 1}. {article.title}
                        </h5>
                        <p className="text-gray-700 dark:text-gray-300 text-sm mb-2">
                          {article.summary}
                        </p>
                        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                          <span>출처: {article.source}</span>
                          <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200"
                          >
                            원문 보기 →
                          </a>
                        </div>

                        {/* 평가 버튼 */}
                        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-gray-600 dark:text-gray-400">이 요약이 도움이 되었나요?</span>
                            {feedbackSubmitted.has(article.url) ? (
                              <span className="text-xs text-green-600 dark:text-green-400">✅ 피드백 완료</span>
                            ) : (
                              <div className="flex space-x-2">
                                <button
                                  onClick={() => submitFeedback(article.title, article.url, "positive")}
                                  disabled={feedbackLoading}
                                  className="text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-200 disabled:opacity-50 text-lg"
                                  title="도움이 되었어요"
                                >
                                  👍
                                </button>
                                <button
                                  onClick={() => submitFeedback(article.title, article.url, "negative")}
                                  disabled={feedbackLoading}
                                  className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-200 disabled:opacity-50 text-lg"
                                  title="별로였어요"
                                >
                                  👎
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {summary && (
            <div className="mt-8 p-6 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
              <h3 className="text-lg font-semibold text-green-800 dark:text-green-200 mb-4">
                ✅ 요약 완료!
              </h3>
              <div className="space-y-4">
                <p className="text-green-700 dark:text-green-300">
                  📧 이메일이 <strong>{formData.recipientEmail}</strong>로 발송되었습니다.
                </p>
                <p className="text-green-700 dark:text-green-300">
                  📊 총 <strong>{summary.total_articles}</strong>개의 기사가 요약되었습니다.
                </p>
              </div>

              {summary.summaries && summary.summaries.length > 0 && (
                <div className="mt-6">
                  <h4 className="text-md font-medium text-green-800 dark:text-green-200 mb-3">
                    📰 요약된 기사 목록:
                  </h4>
                  <div className="space-y-4 max-h-96 overflow-y-auto">
                    {summary.summaries.map((article, index) => (
                      <div key={index} className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow border border-green-200 dark:border-green-700">
                        <h5 className="font-medium text-gray-900 dark:text-white mb-2">
                          {index + 1}. {article.title}
                        </h5>
                        <p className="text-gray-700 dark:text-gray-300 text-sm mb-2">
                          {article.summary}
                        </p>
                        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                          <span>출처: {article.source}</span>
                          <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200"
                          >
                            원문 보기 →
                          </a>
                        </div>

                        {/* 평가 버튼 */}
                        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-gray-600 dark:text-gray-400">이 요약이 도움이 되었나요?</span>
                            {feedbackSubmitted.has(article.url) ? (
                              <span className="text-xs text-green-600 dark:text-green-400">✅ 피드백 완료</span>
                            ) : (
                              <div className="flex space-x-2">
                                <button
                                  onClick={() => submitFeedback(article.title, article.url, "positive")}
                                  disabled={feedbackLoading}
                                  className="text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-200 disabled:opacity-50 text-lg"
                                  title="도움이 되었어요"
                                >
                                  👍
                                </button>
                                <button
                                  onClick={() => submitFeedback(article.title, article.url, "negative")}
                                  disabled={feedbackLoading}
                                  className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-200 disabled:opacity-50 text-lg"
                                  title="별로였어요"
                                >
                                  👎
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SummarizePage;
