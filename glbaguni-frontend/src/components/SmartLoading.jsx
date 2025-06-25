import React from 'react';

const SmartLoading = ({ type = 'fetching', progress = 0, message = '' }) => {
    const loadingStates = {
        fetching: {
            icon: '🔍',
            title: '뉴스를 수집하고 있어요',
            description: 'RSS 피드에서 최신 기사를 가져오는 중...',
            steps: ['피드 연결 중', '기사 수집 중', '데이터 정리 중'],
            color: 'blue'
        },
        summarizing: {
            icon: '🤖',
            title: 'AI가 요약하고 있어요',
            description: '복잡한 내용을 간단하게 만들어드려요',
            steps: ['내용 분석 중', '핵심 추출 중', '요약 생성 중'],
            color: 'purple'
        },
        sending: {
            icon: '📧',
            title: '이메일을 보내고 있어요',
            description: '요약 결과를 메일함으로 전송 중...',
            steps: ['메일 작성 중', '첨부파일 준비 중', '전송 중'],
            color: 'green'
        },
        searching: {
            icon: '🔎',
            title: '뉴스를 검색하고 있어요',
            description: '관련 뉴스를 찾고 있습니다...',
            steps: ['검색 쿼리 처리 중', '결과 필터링 중', '데이터 정리 중'],
            color: 'indigo'
        }
    };

    const state = loadingStates[type] || loadingStates.fetching;
    const currentStep = Math.min(Math.floor(progress * state.steps.length), state.steps.length - 1);

    return (
        <div className="flex flex-col items-center justify-center py-12 px-4">
            {/* 로딩 아이콘 */}
            <div className="relative mb-6">
                <div className={`w-20 h-20 bg-${state.color}-100 dark:bg-${state.color}-900 rounded-full flex items-center justify-center mb-4`}>
                    <div className="animate-bounce text-4xl">{state.icon}</div>
                </div>

                {/* 회전하는 테두리 */}
                <div className={`absolute inset-0 border-4 border-${state.color}-200 border-t-${state.color}-600 rounded-full animate-spin`}></div>
            </div>

            {/* 제목과 설명 */}
            <h3 className={`text-xl font-semibold text-${state.color}-700 dark:text-${state.color}-300 mb-2 text-center`}>
                {state.title}
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6 text-center max-w-md">
                {message || state.description}
            </p>

            {/* 진행 단계 표시 */}
            <div className="w-full max-w-sm">
                {state.steps.map((step, index) => (
                    <div
                        key={index}
                        className={`flex items-center mb-3 transition-all duration-500 ${index <= currentStep
                                ? `text-${state.color}-600 dark:text-${state.color}-400`
                                : 'text-gray-400 dark:text-gray-600'
                            }`}
                    >
                        {/* 단계 아이콘 */}
                        <div className={`w-6 h-6 rounded-full mr-3 flex items-center justify-center transition-all duration-500 ${index < currentStep
                                ? `bg-${state.color}-600 text-white`
                                : index === currentStep
                                    ? `bg-${state.color}-200 dark:bg-${state.color}-800 animate-pulse`
                                    : 'bg-gray-200 dark:bg-gray-700'
                            }`}>
                            {index < currentStep ? (
                                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                </svg>
                            ) : (
                                <div className={`w-2 h-2 rounded-full ${index === currentStep
                                        ? `bg-${state.color}-600 animate-pulse`
                                        : 'bg-gray-400'
                                    }`} />
                            )}
                        </div>

                        {/* 단계 텍스트 */}
                        <span className={`text-sm font-medium ${index === currentStep ? 'animate-pulse' : ''
                            }`}>
                            {step}
                        </span>
                    </div>
                ))}
            </div>

            {/* 진행률 바 */}
            {progress > 0 && (
                <div className="w-full max-w-sm mt-4">
                    <div className="bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                            className={`bg-${state.color}-600 h-2 rounded-full transition-all duration-500 ease-out`}
                            style={{ width: `${Math.min(progress * 100, 100)}%` }}
                        />
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400 mt-2 text-center">
                        {Math.round(progress * 100)}% 완료
                    </div>
                </div>
            )}

            {/* 추가 메시지 */}
            <div className="mt-6 text-center">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                    잠시만 기다려주세요. 보통 30초 내외 소요됩니다.
                </p>
            </div>
        </div>
    );
};

export default SmartLoading; 