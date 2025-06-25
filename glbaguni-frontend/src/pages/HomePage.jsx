import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const HomePage = () => {
  const [visibleFeatures, setVisibleFeatures] = useState([]);
  const [isScrolled, setIsScrolled] = useState(false);

  const features = [
    {
      icon: '📰',
      title: 'RSS 피드 요약',
      description: 'RSS 피드에서 여러 기사를 한 번에 가져와서 간결하게 요약합니다.',
      color: 'from-blue-500 to-blue-600'
    },
    {
      icon: '🔗',
      title: '개별 기사 요약',
      description: '특정 기사 URL을 입력하여 해당 기사만 요약할 수 있습니다.',
      color: 'from-green-500 to-green-600'
    },
    {
      icon: '🌏',
      title: '다국어 지원',
      description: '한국어와 영어로 요약을 제공하여 언어 장벽을 해결합니다.',
      color: 'from-purple-500 to-purple-600'
    },
    {
      icon: '📧',
      title: '이메일 발송',
      description: '요약된 결과를 이메일로 받아볼 수 있어 편리합니다.',
      color: 'from-orange-500 to-orange-600'
    },
    {
      icon: '📖',
      title: '히스토리 관리',
      description: '이전 요약 기록을 저장하고 언제든지 다시 확인할 수 있습니다.',
      color: 'from-indigo-500 to-indigo-600'
    },
    {
      icon: '🎯',
      title: '개인화 추천',
      description: '사용자의 관심사를 바탕으로 맞춤형 뉴스를 추천해드립니다.',
      color: 'from-pink-500 to-pink-600'
    }
  ];

  // 스크롤 애니메이션
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);

      // 기능 카드 애니메이션
      const featureElements = document.querySelectorAll('.feature-card');
      const newVisibleFeatures = [];

      featureElements.forEach((element, index) => {
        const rect = element.getBoundingClientRect();
        if (rect.top < window.innerHeight - 100) {
          newVisibleFeatures.push(index);
        }
      });

      setVisibleFeatures(newVisibleFeatures);
    };

    window.addEventListener('scroll', handleScroll);
    handleScroll(); // 초기 실행

    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 overflow-x-hidden">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        {/* 배경 장식 요소 */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-10 left-10 w-32 h-32 bg-blue-500 rounded-full blur-3xl animate-pulse-slow"></div>
          <div className="absolute bottom-10 right-10 w-40 h-40 bg-purple-500 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-20 lg:py-24">
          <div className="text-center">
            <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 dark:text-white mb-4 sm:mb-6 animate-fade-in">
              <span className="text-blue-600 dark:text-blue-400 block sm:inline">📰 글바구니</span>
              <br className="block sm:hidden" />
              <span className="text-xl sm:text-2xl md:text-3xl lg:text-4xl block mt-2 sm:mt-0">AI 기반 RSS 요약 서비스</span>
            </h1>

            <p className="text-base sm:text-lg md:text-xl text-gray-600 dark:text-gray-300 mb-6 sm:mb-8 max-w-3xl mx-auto px-4 animate-slide-up" style={{ animationDelay: '0.2s' }}>
              복잡한 뉴스들을 간단하게! AI가 여러분의 RSS 피드와 기사를
              <br className="hidden sm:block" />
              <strong className="text-blue-600 dark:text-blue-400">한국어와 영어로 요약</strong>해드립니다.
            </p>

            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center items-center px-4 animate-slide-up" style={{ animationDelay: '0.4s' }}>
              <Link
                to="/summarize"
                className="w-full sm:w-auto bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-bold py-3 sm:py-4 px-6 sm:px-8 rounded-mobile transition-all duration-200 shadow-card hover:shadow-card-hover transform hover:scale-105 min-touch-target touch-manipulation no-tap-highlight"
              >
                📝 지금 요약하기
              </Link>
              <Link
                to="/history"
                className="w-full sm:w-auto border-2 border-blue-600 text-blue-600 hover:bg-blue-600 hover:text-white font-bold py-3 sm:py-4 px-6 sm:px-8 rounded-mobile transition-all duration-200 dark:border-blue-400 dark:text-blue-400 dark:hover:bg-blue-400 dark:hover:text-gray-900 min-touch-target touch-manipulation no-tap-highlight"
              >
                📖 내 히스토리 보기
              </Link>
            </div>

            {/* 모바일 전용 빠른 시작 힌트 */}
            <div className="mt-8 sm:hidden">
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                👆 탭하여 시작하거나 아래로 스크롤하여 더 알아보기
              </p>
              <div className="animate-bounce-subtle">
                <svg className="w-6 h-6 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-12 sm:py-16 bg-white dark:bg-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12 sm:mb-16">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-3 sm:mb-4">
              ✨ 주요 기능
            </h2>
            <p className="text-base sm:text-lg md:text-xl text-gray-600 dark:text-gray-300">
              글바구니가 제공하는 강력한 기능들을 만나보세요
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 lg:gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className={`feature-card bg-gradient-card dark:bg-gradient-card-dark rounded-mobile p-4 sm:p-6 shadow-card hover:shadow-card-hover transition-all duration-300 transform hover:scale-105 cursor-pointer touch-manipulation no-tap-highlight ${visibleFeatures.includes(index) ? 'animate-slide-up opacity-100' : 'opacity-0 translate-y-8'
                  }`}
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <div className={`w-12 h-12 sm:w-16 sm:h-16 bg-gradient-to-r ${feature.color} rounded-full flex items-center justify-center mb-3 sm:mb-4 mx-auto sm:mx-0`}>
                  <span className="text-2xl sm:text-3xl">{feature.icon}</span>
                </div>
                <h3 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-white mb-2 text-center sm:text-left">
                  {feature.title}
                </h3>
                <p className="text-sm sm:text-base text-gray-600 dark:text-gray-300 leading-relaxed text-center sm:text-left">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* How it Works Section */}
      <div className="py-12 sm:py-16 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12 sm:mb-16">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-3 sm:mb-4">
              🚀 사용 방법
            </h2>
            <p className="text-base sm:text-lg md:text-xl text-gray-600 dark:text-gray-300">
              간단한 3단계로 뉴스 요약을 받아보세요
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
            {[
              {
                step: '1',
                title: 'RSS URL 또는 기사 URL 입력',
                description: '요약하고 싶은 RSS 피드나 기사의 URL을 입력하세요.',
                color: 'bg-blue-600'
              },
              {
                step: '2',
                title: '언어 및 옵션 선택',
                description: '한국어 또는 영어 요약을 선택하고 이메일 주소를 입력하세요.',
                color: 'bg-green-600'
              },
              {
                step: '3',
                title: '요약 결과 확인',
                description: 'AI가 생성한 요약을 웹페이지와 이메일로 받아보세요.',
                color: 'bg-purple-600'
              }
            ].map((step, index) => (
              <div key={index} className="text-center">
                <div className={`w-14 h-14 sm:w-16 sm:h-16 ${step.color} text-white rounded-full flex items-center justify-center text-xl sm:text-2xl font-bold mx-auto mb-4 sm:mb-6 shadow-lg transform hover:scale-110 transition-transform duration-200`}>
                  {step.step}
                </div>
                <h3 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-white mb-2 sm:mb-3 px-2">
                  {step.title}
                </h3>
                <p className="text-sm sm:text-base text-gray-600 dark:text-gray-300 leading-relaxed px-4">
                  {step.description}
                </p>
              </div>
            ))}
          </div>

          {/* 모바일 전용 프로세스 플로우 */}
          <div className="mt-12 sm:hidden">
            <div className="flex justify-center space-x-4">
              <div className="flex flex-col items-center">
                <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
                <div className="w-0.5 h-8 bg-gray-300 dark:bg-gray-600 mt-2"></div>
              </div>
              <div className="flex flex-col items-center">
                <div className="w-2 h-2 bg-green-600 rounded-full animate-pulse" style={{ animationDelay: '0.5s' }}></div>
                <div className="w-0.5 h-8 bg-gray-300 dark:bg-gray-600 mt-2"></div>
              </div>
              <div className="flex flex-col items-center">
                <div className="w-2 h-2 bg-purple-600 rounded-full animate-pulse" style={{ animationDelay: '1s' }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-12 sm:py-16 bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-800 dark:to-purple-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-3 sm:mb-4">
            지금 시작해보세요! 🎉
          </h2>
          <p className="text-base sm:text-lg md:text-xl text-blue-100 mb-6 sm:mb-8 px-4">
            복잡한 뉴스를 간단하게 요약받고, 시간을 절약하세요.
          </p>
          <Link
            to="/summarize"
            className="inline-block bg-white text-blue-600 hover:bg-gray-100 font-bold py-3 sm:py-4 px-6 sm:px-8 rounded-mobile transition-all duration-200 shadow-card hover:shadow-card-hover transform hover:scale-105 min-touch-target touch-manipulation no-tap-highlight"
          >
            📝 요약 서비스 시작하기
          </Link>

          {/* 모바일 전용 추가 정보 */}
          <div className="mt-8 sm:hidden">
            <div className="grid grid-cols-2 gap-4 max-w-sm mx-auto">
              <Link
                to="/sources"
                className="bg-white/10 text-white py-2 px-4 rounded-touch text-sm font-medium transition-colors hover:bg-white/20 touch-manipulation"
              >
                📰 뉴스 소스
              </Link>
              <Link
                to="/contact"
                className="bg-white/10 text-white py-2 px-4 rounded-touch text-sm font-medium transition-colors hover:bg-white/20 touch-manipulation"
              >
                📬 문의하기
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage; 