import React, { useState } from 'react';

const ContactPage = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    type: 'feedback',
    message: ''
  });
  const [submitted, setSubmitted] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // TODO: Implement actual contact form submission
    console.log('Contact form submitted:', formData);
    setSubmitted(true);
  };

  const contactTypes = [
    { value: 'feedback', label: '💡 피드백', icon: '💡' },
    { value: 'bug', label: '🐛 버그 제보', icon: '🐛' },
    { value: 'feature', label: '✨ 기능 제안', icon: '✨' },
    { value: 'support', label: '❓ 지원 요청', icon: '❓' },
    { value: 'other', label: '📬 기타 문의', icon: '📬' }
  ];

  if (submitted) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
        <div className="max-w-2xl mx-auto px-4 text-center">
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-8">
            <div className="text-6xl mb-4">✅</div>
            <h2 className="text-2xl font-bold text-green-800 dark:text-green-200 mb-4">
              문의가 전송되었습니다!
            </h2>
            <p className="text-green-700 dark:text-green-300 mb-6">
              소중한 의견 감사합니다. 빠른 시일 내에 검토하여 답변드리겠습니다.
            </p>
            <button
              onClick={() => {
                setSubmitted(false);
                setFormData({ name: '', email: '', type: 'feedback', message: '' });
              }}
              className="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg transition-colors duration-200"
            >
              새 문의 작성하기
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
              📬 문의 & 피드백
            </h1>
            <p className="text-gray-600 dark:text-gray-300">
              글바구니를 더 좋은 서비스로 만들기 위한 여러분의 의견을 기다립니다
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Contact Form */}
            <div>
              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    이름 *
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    required
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="홍길동"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    이메일 주소 *
                  </label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    required
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="your@email.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    문의 유형 *
                  </label>
                  <select
                    name="type"
                    value={formData.type}
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  >
                    {contactTypes.map(type => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    메시지 *
                  </label>
                  <textarea
                    name="message"
                    value={formData.message}
                    onChange={handleInputChange}
                    required
                    rows="6"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="자세한 내용을 작성해주세요..."
                  />
                </div>

                <button
                  type="submit"
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition-colors duration-200"
                >
                  📤 문의 전송
                </button>
              </form>
            </div>

            {/* Contact Info & FAQ */}
            <div className="space-y-6">
              {/* Contact Info */}
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  📞 연락처 정보
                </h3>
                <div className="space-y-3 text-sm text-gray-600 dark:text-gray-300">
                  <div className="flex items-center">
                    <span className="mr-3">📧</span>
                    <span>support@glbaguni.com</span>
                  </div>
                  <div className="flex items-center">
                    <span className="mr-3">⏰</span>
                    <span>응답 시간: 1-2 영업일</span>
                  </div>
                  <div className="flex items-center">
                    <span className="mr-3">🔗</span>
                    <a href="https://github.com/glbaguni" className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200">
                      GitHub Repository
                    </a>
                  </div>
                </div>
              </div>

              {/* Quick FAQ */}
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  ❓ 자주 묻는 질문
                </h3>
                <div className="space-y-4">
                  <details className="cursor-pointer">
                    <summary className="text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400">
                      🤔 요약이 잘못되었어요
                    </summary>
                    <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                      AI 요약의 정확도 향상을 위해 지속적으로 개선하고 있습니다. 구체적인 오류 내용을 알려주시면 더욱 도움이 됩니다.
                    </p>
                  </details>
                  
                  <details className="cursor-pointer">
                    <summary className="text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400">
                      📱 모바일 앱은 언제 출시되나요?
                    </summary>
                    <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                      현재 웹 서비스에 집중하고 있으며, 모바일 앱은 향후 계획에 포함되어 있습니다.
                    </p>
                  </details>
                  
                  <details className="cursor-pointer">
                    <summary className="text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400">
                      💰 유료 플랜이 있나요?
                    </summary>
                    <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                      현재는 무료로 제공되며, 향후 프리미엄 기능을 위한 유료 플랜을 검토 중입니다.
                    </p>
                  </details>
                </div>
              </div>

              {/* Feature Suggestions */}
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-blue-800 dark:text-blue-200 mb-2">
                  💡 기능 제안을 환영합니다!
                </h3>
                <p className="text-sm text-blue-700 dark:text-blue-300 mb-3">
                  글바구니를 더 유용하게 만들 아이디어가 있으시다면 언제든 말씀해주세요.
                </p>
                <div className="text-xs text-blue-600 dark:text-blue-400">
                  <p>• 새로운 언어 지원</p>
                  <p>• 요약 스타일 옵션</p>
                  <p>• 통계 및 분석 기능</p>
                  <p>• 소셜 미디어 연동</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ContactPage;
