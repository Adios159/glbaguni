import React from 'react';

const AccessibleButton = ({
    children,
    onClick,
    disabled = false,
    ariaLabel,
    variant = 'primary',
    size = 'medium',
    type = 'button',
    loading = false,
    className = '',
    icon = null,
    fullWidth = false,
    ...props
}) => {
    const baseClasses = `
    inline-flex items-center justify-center font-medium rounded-lg 
    transition-all duration-200 ease-in-out
    focus:outline-none focus:ring-2 focus:ring-offset-2
    disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none
    transform hover:scale-105 active:scale-95
  `.trim();

    const variants = {
        primary: `
      bg-blue-600 hover:bg-blue-700 text-white
      focus:ring-blue-500 shadow-lg hover:shadow-xl
    `,
        secondary: `
      bg-gray-200 hover:bg-gray-300 text-gray-900 
      dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-white
      focus:ring-gray-500 shadow hover:shadow-lg
    `,
        success: `
      bg-green-600 hover:bg-green-700 text-white
      focus:ring-green-500 shadow-lg hover:shadow-xl
    `,
        danger: `
      bg-red-600 hover:bg-red-700 text-white
      focus:ring-red-500 shadow-lg hover:shadow-xl
    `,
        warning: `
      bg-yellow-500 hover:bg-yellow-600 text-white
      focus:ring-yellow-500 shadow-lg hover:shadow-xl
    `,
        outline: `
      border-2 border-blue-600 text-blue-600 hover:bg-blue-600 hover:text-white
      dark:border-blue-400 dark:text-blue-400 dark:hover:bg-blue-400 dark:hover:text-gray-900
      focus:ring-blue-500 shadow hover:shadow-lg
    `,
        ghost: `
      text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800
      focus:ring-gray-500
    `
    };

    const sizes = {
        small: 'px-3 py-2 text-sm',
        medium: 'px-4 py-2 text-base',
        large: 'px-6 py-3 text-lg'
    };

    const iconSizes = {
        small: 'w-4 h-4',
        medium: 'w-5 h-5',
        large: 'w-6 h-6'
    };

    const buttonClasses = `
    ${baseClasses}
    ${variants[variant] || variants.primary}
    ${sizes[size] || sizes.medium}
    ${fullWidth ? 'w-full' : ''}
    ${className}
  `.replace(/\s+/g, ' ').trim();

    return (
        <button
            type={type}
            onClick={onClick}
            disabled={disabled || loading}
            aria-label={ariaLabel}
            className={buttonClasses}
            {...props}
        >
            {/* 로딩 스피너 */}
            {loading && (
                <svg
                    className={`animate-spin ${iconSizes[size]} mr-2`}
                    fill="none"
                    viewBox="0 0 24 24"
                >
                    <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                    />
                    <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                </svg>
            )}

            {/* 아이콘 (로딩 중이 아닐 때만) */}
            {!loading && icon && (
                <span className={`${children ? 'mr-2' : ''} ${iconSizes[size]}`}>
                    {icon}
                </span>
            )}

            {/* 버튼 텍스트 */}
            {children && (
                <span className={loading ? 'opacity-75' : ''}>
                    {children}
                </span>
            )}
        </button>
    );
};

// 사전 정의된 버튼 variants
export const PrimaryButton = (props) => (
    <AccessibleButton variant="primary" {...props} />
);

export const SecondaryButton = (props) => (
    <AccessibleButton variant="secondary" {...props} />
);

export const SuccessButton = (props) => (
    <AccessibleButton variant="success" {...props} />
);

export const DangerButton = (props) => (
    <AccessibleButton variant="danger" {...props} />
);

export const OutlineButton = (props) => (
    <AccessibleButton variant="outline" {...props} />
);

export const GhostButton = (props) => (
    <AccessibleButton variant="ghost" {...props} />
);

export default AccessibleButton; 