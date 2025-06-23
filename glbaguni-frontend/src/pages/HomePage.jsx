import React from 'react';
import { Link } from 'react-router-dom';

const HomePage = () => {
  const features = [
    {
      icon: '📰',
      title: 'RSS 피드 요약',
      description: 'RSS 피드에서 여러 기사를 한 번에 가져와서 간결하게 요약합니다.'
    },
    {
      icon: '🔗',
      title: '개별 기사 요약',
      description: '특정 기사 URL을 입력하여 해당 기사만 요약할 수 있습니다.'
    },
    {
      icon: '🌏',
      title: '다국어 지원',
      description: '한국어와 영어로 요약을 제공하여 언어 장벽을 해결합니다.'
    },
    {
      icon: '📧',
      title: '이메일 발송',
      description: '요약된 결과를 이메일로 받아볼 수 있어 편리합니다.'
    },
    {
      icon: '📖',
      title: '히스토리 관리',
      description: '이전 요약 기록을 저장하고 언제든지 다시 확인할 수 있습니다.'
    },
    {
      icon: '🎯',
      title: '개인화 추천',
      description: '사용자의 관심사를 바탕으로 맞춤형 뉴스를 추천해드립니다.'
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center">
            <h1 className="text-4xl md:text-6xl font-bold text-gray-900 dark:text-white mb-6">
              <span className="text-blue-600 dark:text-blue-400">📰 글바구니</span>
              <br />
              <span className="text-2xl md:text-4xl">AI 기반 RSS 요약 서비스</span>
            </h1>
            
            <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 max-w-3xl mx-auto">
              복잡한 뉴스들을 간단하게! AI가 여러분의 RSS 피드와 기사를 
              <br />
              <strong className="text-blue-600 dark:text-blue-400">한국어와 영어로 요약</strong>해드립니다.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link
                to="/summarize"
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-8 rounded-lg transition-colors duration-200 shadow-lg hover:shadow-xl"
              >
                📝 지금 요약하기
              </Link>
              <Link
                to="/history"
                className="border-2 border-blue-600 text-blue-600 hover:bg-blue-600 hover:text-white font-bold py-3 px-8 rounded-lg transition-colors duration-200 dark:border-blue-400 dark:text-blue-400 dark:hover:bg-blue-400 dark:hover:text-gray-900"
              >
                📖 내 히스토리 보기
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-16 bg-white dark:bg-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
              ✨ 주요 기능
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300">
              글바구니가 제공하는 강력한 기능들을 만나보세요
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="bg-gray-50 dark:bg-gray-700 rounded-lg p-6 hover:shadow-lg transition-shadow duration-200"
              >
                <div className="text-4xl mb-4">{feature.icon}</div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600 dark:text-gray-300">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* How it Works Section */}
      <div className="py-16 bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
              🚀 사용 방법
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300">
              간단한 3단계로 뉴스 요약을 받아보세요
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                step: '1',
                title: 'RSS URL 또는 기사 URL 입력',
                description: '요약하고 싶은 RSS 피드나 기사의 URL을 입력하세요.'
              },
              {
                step: '2',
                title: '언어 및 옵션 선택',
                description: '한국어 또는 영어 요약을 선택하고 이메일 주소를 입력하세요.'
              },
              {
                step: '3',
                title: '요약 결과 확인',
                description: 'AI가 생성한 요약을 웹페이지와 이메일로 받아보세요.'
              }
            ].map((step, index) => (
              <div key={index} className="text-center">
                <div className="w-16 h-16 bg-blue-600 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4">
                  {step.step}
                </div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                  {step.title}
                </h3>
                <p className="text-gray-600 dark:text-gray-300">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="py-16 bg-blue-600 dark:bg-blue-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            지금 시작해보세요! 🎉
          </h2>
          <p className="text-xl text-blue-100 mb-8">
            복잡한 뉴스를 간단하게 요약받고, 시간을 절약하세요.
          </p>
          <Link
            to="/summarize"
            className="bg-white text-blue-600 hover:bg-gray-100 font-bold py-3 px-8 rounded-lg transition-colors duration-200 shadow-lg hover:shadow-xl"
          >
            📝 요약 서비스 시작하기
          </Link>
        </div>
      </div>
    </div>
  );
};

export default HomePage; 