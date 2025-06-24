import React, { useState, useEffect } from "react";
import axios from "axios";
import { useFormValidation } from "../hooks/useFormValidation";

const SummarizePage = () => {
  const [activeTab, setActiveTab] = useState("search");
  const [healthStatus, setHealthStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isCheckingHealth, setIsCheckingHealth] = useState(false);
  
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

  const { validateForm, validationErrors } = useFormValidation();
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  useEffect(() => {
    if (!localStorage.getItem("user_id")) {
      localStorage.setItem("user_id", crypto.randomUUID());
    }
  }, []);

  const checkBackendHealth = async () => {
    setIsCheckingHealth(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      setHealthStatus(response.data);
      setError(null);
    } catch (err) {
      console.error("Health check failed:", err);
      setHealthStatus(null);
      setError("백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.");
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
      setError("검색어를 입력해주세요.");
      return;
    }

    setIsLoading(true);
    setError(null);
    setNewsResults(null);

    try {
      const requestData = {
        query: newsSearchData.query,
        max_articles: parseInt(newsSearchData.maxArticles),
        language: newsSearchData.language,
        recipient_email: newsSearchData.recipientEmail || null,
        user_id: localStorage.getItem("user_id")
      };

      const response = await axios.post(`${API_BASE_URL}/news-search`, requestData, {
        headers: {
          "Content-Type": "application/json",
        },
        timeout: 300000
      });

      setNewsResults(response.data);
    } catch (err) {
      console.error("Error:", err);
      if (err.response) {
        setError(`서버 오류: ${err.response.status} - ${err.response.data.detail || "알 수 없는 오류"}`);
      } else if (err.request) {
        setError("서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.");
      } else {
        setError(`요청 처리 중 오류가 발생했습니다: ${err.message}`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleRSSSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm(formData)) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setSummary(null);

    try {
      const requestData = {
        rss_urls: formData.rssUrls ? formData.rssUrls.split("\n").filter(url => url.trim()) : null,
        article_urls: formData.articleUrls ? formData.articleUrls.split("\n").filter(url => url.trim()) : null,
        recipient_email: formData.recipientEmail,
        custom_prompt: formData.customPrompt || null,
        max_articles: parseInt(formData.maxArticles),
        language: formData.language,
        user_id: localStorage.getItem("user_id")
      };

      const response = await axios.post(`${API_BASE_URL}/summarize`, requestData, {
        headers: {
          "Content-Type": "application/json",
        },
        timeout: 300000
      });

      setSummary(response.data);
    } catch (err) {
      console.error("Error:", err);
      if (err.response) {
        setError(`서버 오류: ${err.response.status} - ${err.response.data.detail || "알 수 없는 오류"}`);
      } else if (err.request) {
        setError("서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요.");
      } else {
        setError(`요청 처리 중 오류가 발생했습니다: ${err.message}`);
      }
    } finally {
      setIsLoading(false);
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
                  className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === "search"
                      ? "border-blue-500 text-blue-600 dark:text-blue-400"
                      : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300"
                  }`}
                >
                  🔍 자연어 뉴스 검색
                </button>
                <button
                  onClick={() => setActiveTab("rss")}
                  className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === "rss"
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
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  🔍 뉴스 검색어 *
                </label>
                <input
                  type="text"
                  name="query"
                  value={newsSearchData.query}
                  onChange={handleInputChange}
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
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    요약 언어
                  </label>
                  <select
                    name="language"
                    value={newsSearchData.language}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="ko">🇰🇷 한국어</option>
                    <option value="en">🇺🇸 English</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    최대 기사 수
                  </label>
                  <input
                    type="number"
                    name="maxArticles"
                    value={newsSearchData.maxArticles}
                    onChange={handleInputChange}
                    min="1"
                    max="20"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  이메일 주소 (선택사항)
                </label>
                <input
                  type="email"
                  name="recipientEmail"
                  value={newsSearchData.recipientEmail}
                  onChange={handleInputChange}
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
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  RSS 피드 URL (선택사항)
                </label>
                <textarea
                  name="rssUrls"
                  rows="3"
                  value={formData.rssUrls}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="https://feeds.bbci.co.uk/news/rss.xml&#10;각 URL을 새 줄에 입력하세요"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  개별 기사 URL (선택사항)
                </label>
                <textarea
                  name="articleUrls"
                  rows="3"
                  value={formData.articleUrls}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="https://example.com/article1&#10;각 URL을 새 줄에 입력하세요"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  이메일 주소 *
                </label>
                <input
                  type="email"
                  name="recipientEmail"
                  value={formData.recipientEmail}
                  onChange={handleInputChange}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="your@email.com"
                  required
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    요약 언어
                  </label>
                  <select
                    name="language"
                    value={formData.language}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="ko">🇰🇷 한국어</option>
                    <option value="en">🇺🇸 English</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    최대 기사 수
                  </label>
                  <input
                    type="number"
                    name="maxArticles"
                    value={formData.maxArticles}
                    onChange={handleInputChange}
                    min="1"
                    max="50"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  사용자 정의 프롬프트 (선택사항)
                </label>
                <textarea
                  name="customPrompt"
                  rows="3"
                  value={formData.customPrompt}
                  onChange={handleInputChange}
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
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SummarizePage;
