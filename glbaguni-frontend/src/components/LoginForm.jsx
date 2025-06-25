import React, { useState } from 'react';
import axios from 'axios';

const LoginForm = () => {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [token, setToken] = useState('');
  const [user, setUser] = useState(null);

  // API Base URL (환경에 따라 수정)
  const API_BASE_URL = import.meta.env.VITE_API_BASE;

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // FormData 객체 생성 (OAuth2PasswordRequestForm 형식)
      const loginData = new FormData();
      loginData.append('username', formData.username);
      loginData.append('password', formData.password);

      // 로그인 API 호출
      const response = await axios.post(
        `${API_BASE_URL}/auth/login`,
        loginData,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );

      // 성공 응답 처리
      const { access_token, token_type, user: userData } = response.data;

      setToken(access_token);
      setUser(userData);

      // 토큰을 localStorage에 저장
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('token_type', token_type);

      console.log('로그인 성공:', response.data);

    } catch (err) {
      console.error('로그인 오류:', err);

      if (err.response) {
        setError(err.response.data.detail || '로그인에 실패했습니다.');
      } else if (err.request) {
        setError('서버에 연결할 수 없습니다.');
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
    setFormData({ username: '', password: '' });
    localStorage.removeItem('access_token');
    localStorage.removeItem('token_type');
  };

  return (
    <div className="max-w-md mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6 text-center text-gray-800">
        로그인
      </h2>

      {!token ? (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
              사용자명
            </label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleInputChange}
              required
              autoComplete="username"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="사용자명을 입력하세요"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              비밀번호
            </label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleInputChange}
              required
              autoComplete="current-password"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="비밀번호를 입력하세요"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className={`w-full py-2 px-4 rounded-md text-white font-medium ${loading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500'
              }`}
          >
            {loading ? '로그인 중...' : '로그인'}
          </button>
        </form>
      ) : (
        <div className="text-center">
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-md">
            <h3 className="text-lg font-semibold text-green-800 mb-2">로그인 성공!</h3>
            <p className="text-green-700">환영합니다, {user?.username}님!</p>
          </div>

          <button
            onClick={handleLogout}
            className="w-full py-2 px-4 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            로그아웃
          </button>
        </div>
      )}

      {/* 오류 메시지 */}
      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      {/* 토큰 정보 표시 (개발용) */}
      {token && (
        <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-md">
          <h4 className="text-sm font-semibold text-gray-800 mb-2">토큰 정보:</h4>
          <div className="text-xs text-gray-600 break-all">
            <p><strong>Access Token:</strong></p>
            <p className="bg-gray-100 p-2 rounded mt-1">{token}</p>
          </div>
          {user && (
            <div className="mt-3 text-xs text-gray-600">
              <p><strong>사용자 정보:</strong></p>
              <p>ID: {user.id}</p>
              <p>Username: {user.username}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default LoginForm;
