import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const location = useLocation();

  const navItems = [
    { path: '/', icon: '🏠', label: 'Home' },
    { path: '/summarize', icon: '📝', label: 'Summarize' },
    { path: '/history', icon: '📖', label: 'My History' },
    { path: '/recommendations', icon: '🔥', label: 'Recommendations' },
    { path: '/sources', icon: '📰', label: 'News Sources' },
    { path: '/contact', icon: '📬', label: 'Contact' },
    { path: '/login', icon: '🔐', label: 'Login' },
    { path: '/signup', icon: '✨', label: 'Sign Up' }
  ];

  const isActive = (path) => {
    return location.pathname === path;
  };

  const toggleMenu = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  const closeMenu = () => {
    setIsMenuOpen(false);
  };

  // 스크롤 감지
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // 메뉴 외부 클릭 시 닫기
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (isMenuOpen && !event.target.closest('.mobile-menu-container')) {
        setIsMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [isMenuOpen]);

  // 페이지 변경 시 메뉴 닫기
  useEffect(() => {
    setIsMenuOpen(false);
  }, [location.pathname]);

  return (
    <nav className={`bg-white dark:bg-gray-800 shadow-lg border-b border-gray-200 dark:border-gray-700 sticky top-0 z-50 transition-all duration-200 ${isScrolled ? 'bg-white/95 dark:bg-gray-800/95 backdrop-blur-sm' : ''
      }`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link to="/" className="flex items-center space-x-2">
              <span className="text-xl sm:text-2xl font-bold text-blue-600 dark:text-blue-400">
                📰 글바구니
              </span>
            </Link>
          </div>

          {/* Desktop Navigation Links */}
          <div className="hidden lg:flex lg:items-center lg:space-x-6 xl:space-x-8">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-all duration-200 ${isActive(item.path)
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200 shadow-sm'
                    : 'text-gray-700 hover:text-blue-600 dark:text-gray-300 dark:hover:text-blue-400 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
              >
                <span className="mr-2">{item.icon}</span>
                <span className="hidden xl:inline">{item.label}</span>
              </Link>
            ))}
          </div>

          {/* Mobile menu button */}
          <div className="lg:hidden flex items-center mobile-menu-container">
            <button
              type="button"
              onClick={toggleMenu}
              className={`inline-flex items-center justify-center p-3 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 transition-all duration-200 ${isMenuOpen ? 'bg-gray-100 dark:bg-gray-700 text-gray-500' : ''
                }`}
              aria-expanded="false"
              aria-label="메인 메뉴"
            >
              <span className="sr-only">Open main menu</span>
              <div className="relative w-6 h-6">
                <span
                  className={`absolute block h-0.5 w-6 bg-current transform transition duration-200 ease-in-out ${isMenuOpen ? 'rotate-45 top-3' : 'top-1'
                    }`}
                />
                <span
                  className={`absolute block h-0.5 w-6 bg-current transform transition duration-200 ease-in-out top-3 ${isMenuOpen ? 'opacity-0' : 'opacity-100'
                    }`}
                />
                <span
                  className={`absolute block h-0.5 w-6 bg-current transform transition duration-200 ease-in-out ${isMenuOpen ? '-rotate-45 top-3' : 'top-5'
                    }`}
                />
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      <div className={`lg:hidden mobile-menu-container transition-all duration-300 ease-in-out ${isMenuOpen ? 'max-h-screen opacity-100' : 'max-h-0 opacity-0'
        } overflow-hidden`}>
        <div className="px-2 pt-2 pb-3 space-y-1 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 shadow-lg">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              onClick={closeMenu}
              className={`block px-4 py-3 text-base font-medium rounded-lg transition-all duration-200 touch-manipulation ${isActive(item.path)
                  ? 'bg-blue-50 border-l-4 border-blue-500 text-blue-700 dark:bg-blue-900/50 dark:text-blue-200 dark:border-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 hover:bg-gray-50 dark:text-gray-300 dark:hover:text-gray-200 dark:hover:bg-gray-700'
                }`}
            >
              <div className="flex items-center">
                <span className="mr-3 text-lg">{item.icon}</span>
                <span>{item.label}</span>
                {isActive(item.path) && (
                  <span className="ml-auto">
                    <svg className="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>

        {/* 모바일 메뉴 하단 빠른 액션 */}
        <div className="px-4 py-3 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">빠른 액션</div>
          <div className="grid grid-cols-2 gap-2">
            <Link
              to="/summarize"
              onClick={closeMenu}
              className="flex items-center justify-center px-3 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors touch-manipulation"
            >
              <span className="mr-1">📝</span>
              요약하기
            </Link>
            <Link
              to="/history"
              onClick={closeMenu}
              className="flex items-center justify-center px-3 py-2 bg-gray-600 text-white rounded-md text-sm font-medium hover:bg-gray-700 transition-colors touch-manipulation"
            >
              <span className="mr-1">📖</span>
              히스토리
            </Link>
          </div>
        </div>
      </div>

      {/* 모바일 메뉴 오버레이 */}
      {isMenuOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black bg-opacity-25 z-40"
          onClick={closeMenu}
        />
      )}
    </nav>
  );
};

export default Navbar; 