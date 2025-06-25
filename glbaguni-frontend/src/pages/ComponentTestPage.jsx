import React, { useState } from 'react';
import { useToast } from '../hooks/useToast';
import SmartLoading from '../components/SmartLoading';
import EmptyState from '../components/EmptyState';
import AccessibleButton from '../components/AccessibleButton';

const ComponentTestPage = () => {
    const [showLoading, setShowLoading] = useState(false);
    const [loadingType, setLoadingType] = useState('fetching');
    const [loadingProgress, setLoadingProgress] = useState(0);
    const [emptyStateType, setEmptyStateType] = useState('history');

    const { showSuccess, showError, showWarning, showInfo } = useToast();

    const simulateLoading = () => {
        setShowLoading(true);
        setLoadingProgress(0);

        const interval = setInterval(() => {
            setLoadingProgress(prev => {
                if (prev >= 1) {
                    clearInterval(interval);
                    setShowLoading(false);
                    showSuccess("로딩 완료!");
                    return 1;
                }
                return prev + 0.1;
            });
        }, 500);
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
            <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8 text-center">
                        🧪 UX 컴포넌트 테스트 페이지
                    </h1>

                    {/* 토스트 알림 테스트 */}
                    <section className="mb-12">
                        <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
                            📢 토스트 알림 시스템
                        </h2>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <AccessibleButton
                                onClick={() => showSuccess("성공 메시지입니다!", { title: "성공!" })}
                                variant="success"
                            >
                                ✅ 성공
                            </AccessibleButton>
                            <AccessibleButton
                                onClick={() => showError("오류 메시지입니다!", { title: "오류 발생" })}
                                variant="danger"
                            >
                                ❌ 오류
                            </AccessibleButton>
                            <AccessibleButton
                                onClick={() => showWarning("주의 메시지입니다!", { title: "주의" })}
                                variant="warning"
                            >
                                ⚠️ 경고
                            </AccessibleButton>
                            <AccessibleButton
                                onClick={() => showInfo("정보 메시지입니다!", { title: "정보" })}
                                variant="primary"
                            >
                                ℹ️ 정보
                            </AccessibleButton>
                        </div>
                    </section>

                    {/* 스마트 로딩 테스트 */}
                    <section className="mb-12">
                        <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
                            ⏳ 스마트 로딩 상태
                        </h2>

                        <div className="mb-4 flex flex-wrap gap-4">
                            <select
                                value={loadingType}
                                onChange={(e) => setLoadingType(e.target.value)}
                                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                            >
                                <option value="fetching">피드 수집</option>
                                <option value="summarizing">AI 요약</option>
                                <option value="sending">이메일 발송</option>
                                <option value="searching">뉴스 검색</option>
                            </select>

                            <AccessibleButton
                                onClick={simulateLoading}
                                disabled={showLoading}
                                variant="primary"
                            >
                                로딩 시뮬레이션 시작
                            </AccessibleButton>

                            <AccessibleButton
                                onClick={() => setShowLoading(!showLoading)}
                                variant="outline"
                            >
                                {showLoading ? '로딩 숨기기' : '로딩 보이기'}
                            </AccessibleButton>
                        </div>

                        {showLoading && (
                            <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-4">
                                <SmartLoading
                                    type={loadingType}
                                    progress={loadingProgress}
                                />
                            </div>
                        )}
                    </section>

                    {/* 빈 상태 테스트 */}
                    <section className="mb-12">
                        <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
                            📭 빈 상태 (Empty State)
                        </h2>

                        <div className="mb-4 flex flex-wrap gap-4">
                            <select
                                value={emptyStateType}
                                onChange={(e) => setEmptyStateType(e.target.value)}
                                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                            >
                                <option value="history">히스토리 없음</option>
                                <option value="recommendations">추천 없음</option>
                                <option value="sources">소스 없음</option>
                                <option value="search">검색 결과 없음</option>
                                <option value="error">에러 상태</option>
                                <option value="loading">로딩 상태</option>
                            </select>
                        </div>

                        <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-4">
                            <EmptyState type={emptyStateType} />
                        </div>
                    </section>

                    {/* 접근성 버튼 테스트 */}
                    <section className="mb-12">
                        <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
                            🔘 접근성 개선 버튼
                        </h2>

                        <div className="space-y-6">
                            {/* 버튼 변형 */}
                            <div>
                                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-3">
                                    버튼 스타일 변형
                                </h3>
                                <div className="flex flex-wrap gap-3">
                                    <AccessibleButton variant="primary">Primary</AccessibleButton>
                                    <AccessibleButton variant="secondary">Secondary</AccessibleButton>
                                    <AccessibleButton variant="success">Success</AccessibleButton>
                                    <AccessibleButton variant="danger">Danger</AccessibleButton>
                                    <AccessibleButton variant="outline">Outline</AccessibleButton>
                                    <AccessibleButton variant="ghost">Ghost</AccessibleButton>
                                </div>
                            </div>

                            {/* 버튼 크기 */}
                            <div>
                                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-3">
                                    버튼 크기
                                </h3>
                                <div className="flex flex-wrap items-center gap-3">
                                    <AccessibleButton size="small">Small</AccessibleButton>
                                    <AccessibleButton size="medium">Medium</AccessibleButton>
                                    <AccessibleButton size="large">Large</AccessibleButton>
                                </div>
                            </div>

                            {/* 아이콘과 로딩 */}
                            <div>
                                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-3">
                                    아이콘 및 로딩 상태
                                </h3>
                                <div className="flex flex-wrap gap-3">
                                    <AccessibleButton icon="🔍">검색</AccessibleButton>
                                    <AccessibleButton icon="💾" variant="success">저장</AccessibleButton>
                                    <AccessibleButton loading={true}>로딩 중...</AccessibleButton>
                                    <AccessibleButton disabled={true}>비활성화</AccessibleButton>
                                </div>
                            </div>

                            {/* 전체 너비 */}
                            <div>
                                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-3">
                                    전체 너비 버튼
                                </h3>
                                <AccessibleButton fullWidth variant="primary" size="large">
                                    전체 너비 버튼 예시
                                </AccessibleButton>
                            </div>
                        </div>
                    </section>

                    {/* 사용 팁 */}
                    <section>
                        <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
                            💡 구현된 UX 개선사항
                        </h2>
                        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
                            <ul className="space-y-2 text-sm text-blue-800 dark:text-blue-200">
                                <li>✅ <strong>스마트 로딩:</strong> 진행 단계별 시각적 피드백</li>
                                <li>✅ <strong>토스트 알림:</strong> 자동 닫힘과 수동 제어 가능</li>
                                <li>✅ <strong>빈 상태:</strong> 상황별 맞춤 안내 메시지</li>
                                <li>✅ <strong>접근성 버튼:</strong> 키보드 네비게이션 및 스크린 리더 지원</li>
                                <li>✅ <strong>반응형 디자인:</strong> 모든 화면 크기에서 최적화</li>
                                <li>✅ <strong>다크 모드:</strong> 완전한 다크 테마 지원</li>
                            </ul>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
};

export default ComponentTestPage; 