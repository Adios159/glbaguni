import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const EmptyState = ({ type, customConfig = null, onRetry = null }) => {
    const [isVisible, setIsVisible] = useState(false);
    const [isRetrying, setIsRetrying] = useState(false);

    useEffect(() => {
        setIsVisible(true);
    }, []);

    const emptyStates = {
        history: {
            icon: '📚',
            title: '아직 요약 기록이 없어요',
            description: '첫 번째 요약을 시작해보세요! RSS 피드나 기사 URL을 입력하면 AI가 간결하게 요약해드립니다.',
            action: '요약 시작하기',
            actionPath: '/summarize',
            actionIcon: '✨',
            helpText: 'RSS URL이나 기사 URL을 입력하면 몇 초 만에 요약을 받을 수 있어요.',
            secondaryActions: [
                { label: '샘플 RSS 보기', path: '/sources' },
                { label: '사용법 알아보기', path: '/' }
            ]
        },
        recommendations: {
            icon: '🎯',
            title: '추천 뉴스가 준비 중이에요',
            description: '더 많은 요약을 하면 맞춤형 추천을 받을 수 있어요. 관심사를 파악해서 더 나은 뉴스를 추천해드릴게요.',
            action: '뉴스 요약하기',
            actionPath: '/summarize',
            actionIcon: '🔍',
            helpText: '3-5개의 기사를 요약하면 개인화된 추천을 시작해드려요.',
            secondaryActions: [
                { label: '인기 뉴스 소스', path: '/sources' }
            ]
        },
        sources: {
            icon: '📰',
            title: '즐겨찾는 뉴스 소스가 없어요',
            description: '자주 이용하는 RSS 피드나 뉴스 사이트를 즐겨찾기에 추가해보세요.',
            action: '소스 추가하기',
            actionPath: '/sources',
            actionIcon: '➕',
            helpText: '신뢰할 수 있는 뉴스 소스를 미리 등록하면 빠르게 요약할 수 있어요.',
            secondaryActions: [
                { label: '추천 RSS 피드', path: '/sources' }
            ]
        },
        search: {
            icon: '🔎',
            title: '검색 결과가 없어요',
            description: '다른 검색어로 시도해보시거나 더 일반적인 키워드를 사용해보세요.',
            action: '새로 검색하기',
            actionPath: '/summarize',
            actionIcon: '🔄',
            helpText: '키워드를 바꾸거나 RSS URL을 직접 입력해보세요.',
            secondaryActions: [
                { label: '인기 검색어', path: '/recommendations' }
            ]
        },
        error: {
            icon: '😵',
            title: '문제가 발생했어요',
            description: '일시적인 오류일 수 있습니다. 잠시 후 다시 시도해주세요.',
            action: '다시 시도',
            actionPath: null,
            actionIcon: '🔄',
            helpText: '계속 문제가 발생하면 다른 URL을 시도하거나 고객센터에 문의해주세요.',
            secondaryActions: [
                { label: '문의하기', path: '/contact' },
                { label: '서비스 상태', path: '/' }
            ]
        },
        loading: {
            icon: '⏳',
            title: '데이터를 불러오는 중...',
            description: '잠시만 기다려주세요.',
            action: null,
            actionPath: null,
            actionIcon: null
        },
        network: {
            icon: '📡',
            title: '인터넷 연결을 확인해주세요',
            description: '네트워크 연결에 문제가 있는 것 같습니다. 연결 상태를 확인하고 다시 시도해주세요.',
            action: '다시 시도',
            actionPath: null,
            actionIcon: '🔄',
            helpText: 'WiFi나 모바일 데이터 연결을 확인해보세요.',
            secondaryActions: [
                { label: '캐시된 데이터 보기', path: '/history' }
            ]
        }
    };

    const config = customConfig || emptyStates[type] || emptyStates.error;

    const handleAction = async () => {
        if (config.actionPath) {
            // React Router 링크로 처리됨
        } else if (onRetry) {
            setIsRetrying(true);
            try {
                await onRetry();
            } catch (error) {
                console.error('Retry failed:', error);
            } finally {
                setIsRetrying(false);
            }
        } else {
            window.location.reload();
        }
    };

    return (
        <div className={`flex flex-col items-center justify-center py-12 sm:py-16 px-4 text-center transition-all duration-700 transform ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
            }`}>
            {/* 애니메이션 아이콘 */}
            <div className="relative mb-6 sm:mb-8">
                <div className="w-20 h-20 sm:w-24 sm:h-24 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 rounded-full flex items-center justify-center shadow-lg animate-pulse">
                    <span className="text-3xl sm:text-4xl animate-bounce">{config.icon}</span>
                </div>

                {/* 장식용 원형 */}
                <div className="absolute -inset-2 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-full animate-pulse" />
            </div>

            {/* 제목 */}
            <h3 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-white mb-2 sm:mb-3 px-2">
                {config.title}
            </h3>

            {/* 설명 */}
            <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400 mb-6 sm:mb-8 max-w-md leading-relaxed px-2">
                {config.description}
            </p>

            {/* 액션 버튼 */}
            {config.action && (
                <div className="space-y-4 w-full max-w-sm">
                    {config.actionPath ? (
                        <Link
                            to={config.actionPath}
                            className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-medium rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                        >
                            {config.actionIcon && (
                                <span className="mr-2 text-lg">{config.actionIcon}</span>
                            )}
                            {config.action}
                        </Link>
                    ) : (
                        <button
                            onClick={handleAction}
                            disabled={isRetrying}
                            className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-gray-400 disabled:to-gray-500 text-white font-medium rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105 disabled:transform-none disabled:hover:scale-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                        >
                            {isRetrying ? (
                                <>
                                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    처리 중...
                                </>
                            ) : (
                                <>
                                    {config.actionIcon && (
                                        <span className="mr-2 text-lg">{config.actionIcon}</span>
                                    )}
                                    {config.action}
                                </>
                            )}
                        </button>
                    )}

                    {/* 보조 액션들 */}
                    {config.secondaryActions && (
                        <div className="flex flex-col sm:flex-row flex-wrap justify-center gap-2 sm:gap-3 mt-4">
                            {config.secondaryActions.map((action, index) => (
                                <Link
                                    key={index}
                                    to={action.path}
                                    className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium transition-colors duration-200 hover:underline px-2 py-1"
                                >
                                    {action.label}
                                </Link>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* 도움말 섹션 */}
            {config.helpText && (
                <div className="mt-6 sm:mt-8 p-4 bg-gradient-to-r from-gray-50 to-blue-50 dark:from-gray-800 dark:to-blue-900/20 rounded-lg max-w-md w-full mx-2">
                    <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2 flex items-center justify-center">
                        <span className="mr-2">💡</span>
                        도움말
                    </h4>
                    <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                        {config.helpText}
                    </p>
                </div>
            )}

            {/* 모바일 전용 빠른 액션 */}
            {type === 'history' && (
                <div className="mt-6 sm:hidden w-full max-w-sm space-y-2">
                    <Link
                        to="/sources"
                        className="w-full flex items-center justify-center px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                    >
                        <span className="mr-2">📰</span>
                        인기 뉴스 소스 보기
                    </Link>
                    <Link
                        to="/recommendations"
                        className="w-full flex items-center justify-center px-4 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                    >
                        <span className="mr-2">🔥</span>
                        추천 받기
                    </Link>
                </div>
            )}
        </div>
    );
};

export default EmptyState; 