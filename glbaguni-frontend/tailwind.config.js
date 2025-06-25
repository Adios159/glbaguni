/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // 모바일 최적화 브레이크포인트
      screens: {
        'xs': '475px',
        'sm': '640px',
        'md': '768px',
        'lg': '1024px',
        'xl': '1280px',
        '2xl': '1536px',
        // 터치 디바이스 감지
        'touch': { 'raw': '(hover: none)' },
        'no-touch': { 'raw': '(hover: hover)' },
      },

      // 터치 친화적 크기
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        'touch': '44px', // 최소 터치 타겟 크기 (Apple HIG)
      },

      // 모바일 최적화 폰트 크기
      fontSize: {
        'xs-mobile': ['0.75rem', { lineHeight: '1.25rem' }],
        'sm-mobile': ['0.875rem', { lineHeight: '1.375rem' }],
        'base-mobile': ['1rem', { lineHeight: '1.5rem' }],
        'lg-mobile': ['1.125rem', { lineHeight: '1.625rem' }],
        'xl-mobile': ['1.25rem', { lineHeight: '1.75rem' }],
      },

      // 애니메이션 개선
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-subtle': 'bounceSubtle 2s ease-in-out infinite',
      },

      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        bounceSubtle: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        },
      },

      // 그라디언트 색상
      backgroundImage: {
        'gradient-mobile': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'gradient-card': 'linear-gradient(145deg, #ffffff 0%, #f8fafc 100%)',
        'gradient-card-dark': 'linear-gradient(145deg, #1f2937 0%, #111827 100%)',
      },

      // 그림자 개선
      boxShadow: {
        'card': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'card-hover': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        'mobile': '0 2px 8px rgba(0, 0, 0, 0.1)',
        'touch': '0 2px 4px rgba(0, 0, 0, 0.1)',
      },

      // 모바일 최적화 border radius
      borderRadius: {
        'mobile': '0.75rem',
        'touch': '0.5rem',
      },
    },
  },
  plugins: [
    // 터치 디바이스 최적화 유틸리티
    function ({ addUtilities }) {
      const touchUtilities = {
        '.touch-manipulation': {
          'touch-action': 'manipulation',
        },
        '.touch-pan-x': {
          'touch-action': 'pan-x',
        },
        '.touch-pan-y': {
          'touch-action': 'pan-y',
        },
        '.touch-none': {
          'touch-action': 'none',
        },
        // 터치 타겟 크기 보장
        '.min-touch-target': {
          'min-height': '44px',
          'min-width': '44px',
        },
        // 스크롤바 숨기기
        '.hide-scrollbar': {
          '-ms-overflow-style': 'none',
          'scrollbar-width': 'none',
          '&::-webkit-scrollbar': {
            display: 'none',
          },
        },
        // iOS Safari 최적화
        '.ios-scroll': {
          '-webkit-overflow-scrolling': 'touch',
        },
        // 텍스트 선택 방지
        '.no-select': {
          '-webkit-user-select': 'none',
          '-moz-user-select': 'none',
          '-ms-user-select': 'none',
          'user-select': 'none',
        },
        // 탭 하이라이트 제거
        '.no-tap-highlight': {
          '-webkit-tap-highlight-color': 'transparent',
        },
      };

      addUtilities(touchUtilities);
    },
  ],
}

