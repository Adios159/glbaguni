import React, { useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

const LoginPage = () => {
  const [isLogin, setIsLogin] = useState(true); // true: 로그인, false: 회원가입
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [token, setToken] = useState('');
  const [user, setUser] = useState(null);

  // API Base URL (Vite 환경변수 사용)
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // 입력 시 에러 메시지 클리어
    if (error) setError('');
    if (success) setSuccess('');
  };

  const validateForm = () => {
    // 이메일 검증
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!formData.email || !emailRegex.test(formData.email)) {
      setError('올바른 이메일 주소를 입력해주세요.');
      return false;
    }
    
    if (!isLogin) {
      // 회원가입 시에만 강화된 비밀번호 검증 적용
      if (!formData.password || formData.password.length < 10) {
        setError('비밀번호는 최소 10자 이상이어야 합니다.');
        return false;
      }
      
      // 영어 대문자 확인
      if (!/[A-Z]/.test(formData.password)) {
        setError('비밀번호에 영어 대문자가 1개 이상 포함되어야 합니다.');
        return false;
      }
      
      // 특수문자 확인
      if (!/[!@#$%^&*(),.?":{}|<>]/.test(formData.password)) {
        setError('비밀번호에 특수문자(!@#$%^&*(),.?\":{}|<>)가 1개 이상 포함되어야 합니다.');
        return false;
      }
      
      if (formData.password !== formData.confirmPassword) {
        setError('비밀번호가 일치하지 않습니다.');
        return false;
      }
    } else {
      // 로그인 시에는 기본 검증만
      if (!formData.password) {
        setError('비밀번호를 입력해주세요.');
        return false;
      }
    }
    
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    if (!validateForm()) {
      setLoading(false);
      return;
    }

    try {
      if (isLogin) {
        // 로그인 처리
        const loginData = new FormData();
        loginData.append('username', formData.email); // OAuth2 표준에서는 username 필드 사용
        loginData.append('password', formData.password);

        const response = await axios.post(
          `${API_BASE_URL}/auth/login`,
          loginData,
          {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
          }
        );

        const { access_token, token_type, user: userData } = response.data;
        
        setToken(access_token);
        setUser(userData);
        setSuccess('로그인에 성공했습니다!');
        
        // 토큰 저장
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('token_type', token_type);
        localStorage.setItem('user_id', userData.id);

      } else {
        // 회원가입 처리
        const response = await axios.post(
          `${API_BASE_URL}/auth/register`,
          {
            email: formData.email,
            password: formData.password
          },
          {
            headers: {
              'Content-Type': 'application/json',
            },
          }
        );

        setSuccess('회원가입이 완료되었습니다! 로그인해주세요.');
        setIsLogin(true); // 회원가입 후 로그인 모드로 전환
        setFormData({ email: formData.email, password: '', confirmPassword: '' });
      }

    } catch (err) {
      console.error('API 오류:', err);
      
      if (err.response) {
        setError(err.response.data.detail || `${isLogin ? '로그인' : '회원가입'}에 실패했습니다.`);
      } else if (err.request) {
        setError('서버에 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.');
      } else {
        setError('요청 처리 중 오류가 발생했습니다.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    setToken('');
    setUser(null);
    setFormData({ email: '', password: '', confirmPassword: '' });
    setSuccess('');
    setError('');
    localStorage.removeItem('access_token');
    localStorage.removeItem('token_type');
    localStorage.removeItem('user_id');
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setError('');
    setSuccess('');
    setFormData({ email: '', password: '', confirmPassword: '' });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-12 w-12 text-4xl text-center">📰</div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900 dark:text-white">
            글바구니
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
            AI 기반 뉴스 요약 서비스
          </p>
        </div>

        {!token ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8">
            <div className="flex justify-center mb-6">
              <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
                <button
                  onClick={() => setIsLogin(true)}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    isLogin
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
                  }`}
                >
                  로그인
                </button>
                <button
                  onClick={() => setIsLogin(false)}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    !isLogin
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
                  }`}
                >
                  회원가입
                </button>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  이메일
                </label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="example@domain.com"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  비밀번호
                </label>
                <input
                  type="password"
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  required
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  placeholder="비밀번호 (10자 이상, 영어 대문자 포함, 특수문자 포함)"
                />
                {!isLogin && (
                  <div className="mt-2 text-xs text-gray-600 dark:text-gray-400">
                    <p className="font-medium mb-1">비밀번호 요구사항:</p>
                    <ul className="list-disc list-inside space-y-1">
                      <li>최소 10자 이상</li>
                      <li>영어 대문자 1개 이상</li>
                      <li>특수문자 1개 이상 (!@#$%^&*(),.?\":{}|&lt;&gt;)</li>
                    </ul>
                  </div>
                )}
              </div>

              {!isLogin && (
                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    비밀번호 확인
                  </label>
                  <input
                    type="password"
                    id="confirmPassword"
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleInputChange}
                    required
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                    placeholder="비밀번호 다시 입력"
                  />
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
                  loading
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
                }`}
              >
                {loading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    {isLogin ? '로그인 중...' : '회원가입 중...'}
                  </>
                ) : (
                  isLogin ? '로그인' : '회원가입'
                )}
              </button>
            </form>

            {/* 성공 메시지 */}
            {success && (
              <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md">
                <p className="text-green-700 dark:text-green-300 text-sm">{success}</p>
              </div>
            )}

            {/* 오류 메시지 */}
            {error && (
              <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
                <p className="text-red-700 dark:text-red-300 text-sm">{error}</p>
              </div>
            )}

            {/* 회원가입 링크 */}
            <div className="mt-6">
              <div className="text-center">
                <span className="text-gray-600 dark:text-gray-400 text-sm">
                  계정이 없으신가요?{' '}
                </span>
                <Link
                  to="/signup"
                  className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300"
                >
                  회원가입하기
                </Link>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8">
            <div className="text-center">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 dark:bg-green-900/20 mb-4">
                <svg className="h-6 w-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                로그인 성공!
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                환영합니다, <span className="font-semibold">{user?.email}</span>님!
              </p>
              
              <div className="space-y-4">
                <button
                  onClick={() => window.location.href = '/'}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg transition-colors duration-200"
                >
                  홈으로 이동
                </button>
                <button
                  onClick={handleLogout}
                  className="w-full bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded-lg transition-colors duration-200"
                >
                  로그아웃
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 개발자 정보 */}
        <div className="text-center">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            백엔드 서버: {API_BASE_URL}
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
