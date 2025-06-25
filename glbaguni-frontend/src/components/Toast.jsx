import React, { useEffect, useState } from 'react';

const Toast = ({ id, type = 'info', title, message, duration = 5000, onClose }) => {
    const [isVisible, setIsVisible] = useState(false);
    const [isLeaving, setIsLeaving] = useState(false);

    useEffect(() => {
        // 애니메이션을 위해 약간 지연 후 보이기
        setTimeout(() => setIsVisible(true), 100);

        if (duration > 0) {
            const timer = setTimeout(() => {
                handleClose();
            }, duration);

            return () => clearTimeout(timer);
        }
    }, [duration]);

    const handleClose = () => {
        setIsLeaving(true);
        setTimeout(() => {
            onClose?.(id);
        }, 300);
    };

    const toastTypes = {
        success: {
            icon: '✅',
            bgColor: 'bg-green-500',
            borderColor: 'border-green-400',
            textColor: 'text-white',
            progressColor: 'bg-green-300'
        },
        error: {
            icon: '❌',
            bgColor: 'bg-red-500',
            borderColor: 'border-red-400',
            textColor: 'text-white',
            progressColor: 'bg-red-300'
        },
        warning: {
            icon: '⚠️',
            bgColor: 'bg-yellow-500',
            borderColor: 'border-yellow-400',
            textColor: 'text-white',
            progressColor: 'bg-yellow-300'
        },
        info: {
            icon: 'ℹ️',
            bgColor: 'bg-blue-500',
            borderColor: 'border-blue-400',
            textColor: 'text-white',
            progressColor: 'bg-blue-300'
        }
    };

    const config = toastTypes[type] || toastTypes.info;

    return (
        <div
            className={`
        fixed z-50 max-w-sm w-full transition-all duration-300 ease-out
        ${isVisible && !isLeaving ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
        ${config.bgColor} ${config.borderColor} ${config.textColor}
        rounded-lg shadow-lg border-l-4 p-4 mb-4
      `}
            style={{
                right: isVisible && !isLeaving ? '1rem' : '-100%',
                top: `${Math.max(0, (parseInt(id) || 0) * 80 + 80)}px`
            }}
        >
            <div className="flex items-start">
                {/* 아이콘 */}
                <div className="flex-shrink-0 mr-3">
                    <span className="text-xl">{config.icon}</span>
                </div>

                {/* 메시지 콘텐츠 */}
                <div className="flex-1 min-w-0">
                    {title && (
                        <h4 className="font-semibold text-sm mb-1">{title}</h4>
                    )}
                    <p className="text-sm opacity-90">{message}</p>
                </div>

                {/* 닫기 버튼 */}
                <button
                    onClick={handleClose}
                    className="flex-shrink-0 ml-3 text-white hover:text-gray-200 transition-colors"
                    aria-label="닫기"
                >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path
                            fillRule="evenodd"
                            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                            clipRule="evenodd"
                        />
                    </svg>
                </button>
            </div>

            {/* 진행률 바 (자동 닫힘 표시) */}
            {duration > 0 && (
                <div className="mt-3 h-1 bg-black bg-opacity-20 rounded-full overflow-hidden">
                    <div
                        className={`h-full ${config.progressColor} transition-all ease-linear`}
                        style={{
                            width: '100%',
                            animation: `shrink ${duration}ms linear forwards`
                        }}
                    />
                </div>
            )}

            <style jsx>{`
        @keyframes shrink {
          from {
            width: 100%;
          }
          to {
            width: 0%;
          }
        }
      `}</style>
        </div>
    );
};

export default Toast; 