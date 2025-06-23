import React from 'react';
import { useTheme } from '../hooks/useTheme';

const ThemeToggle = () => {
  const { isDarkMode, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700 dark:focus:ring-blue-600 transition-colors duration-200"
      aria-label={isDarkMode ? '밝은 모드로 전환' : '다크 모드로 전환'}
    >
      {isDarkMode ? (
        <>
          <span className="text-lg mr-2">☀️</span>
          <span>밝은 모드</span>
        </>
      ) : (
        <>
          <span className="text-lg mr-2">🌙</span>
          <span>다크 모드</span>
        </>
      )}
    </button>
  );
};

export default ThemeToggle; 