import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const LoginPage = () => {
  const navigate = useNavigate();
  const API_BASE_URL = import.meta.env.VITE_API_BASE;

  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    username: '',
    confirmPassword: '',
    nickname: '',
    birth_year: '',
    gender: '',
    interests: [],
    need: ''
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [token, setToken] = useState(localStorage.getItem('access_token') || '');
  const [user, setUser] = useState(null);

  // 관심사 옵션들
  const interestOptions = [
    "음악", "산책", "글쓰기", "독서", "영화", "운동", "요리", "여행",
    "게임", "그림", "사진", "춤", "노래", "악기연주", "프로그래밍",
    "언어학습", "반려동물", "가드닝", "수공예", "명상"
  ];

  // 필요사항 옵션들
  const needOptions = [
    "감정 안정", "스트레스 해소", "우울감 완화", "불안감 해소",
    "자신감 향상", "인간관계 개선", "집중력 향상", "수면 개선",
    "분노 조절", "트라우마 극복", "중독 극복", "기타"
  ];

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    setError('');
  };

  const handleInterestChange = (interest) => {
    setFormData(prev => {
      const currentInterests = prev.interests;
      if (currentInterests.includes(interest)) {
        return {
          ...prev,
          interests: currentInterests.filter(item => item !== interest)
        };
      } else {
        if (currentInterests.length >= 10) {
          setError('관심사는 최대 10개까지 선택 가능합니다.');
          return prev;
        }
        return {
          ...prev,
          interests: [...currentInterests, interest]
        };
      }
    });
    setError('');
  };

  const validateLoginForm = () => {
    // 로그인시에는 기본 검증만
    if (!formData.email) {
      setError('이메일을 입력해주세요.');
      return false;
    }

    if (!formData.password) {
      setError('비밀번호를 입력해주세요.');
      return false;
    }

    return true;
  };

  const validateSignupForm = () => {
    // 사용자명 검증
    if (!formData.username || formData.username.length < 3) {
      setError('사용자명은 최소 3자 이상이어야 합니다.');
      return false;
    }

    if (!/^[a-zA-Z0-9_]+$/.test(formData.username)) {
      setError('사용자명은 영문, 숫자, 언더스코어(_)만 사용 가능합니다.');
      return false;
    }

    // 이메일 검증
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!formData.email || !emailRegex.test(formData.email)) {
      setError('올바른 이메일 주소를 입력해주세요.');
      return false;
    }

    // 출생년도 검증 (선택사항이지만 입력했다면 검증)
    if (formData.birth_year) {
      const birthYear = parseInt(formData.birth_year);
      const currentYear = new Date().getFullYear();
      const age = currentYear - birthYear;

      if (birthYear < 1900 || birthYear > currentYear) {
        setError(`출생년도는 1900년부터 ${currentYear}년까지 입력 가능합니다.`);
        return false;
      }

      if (age < 14) {
        setError('만 14세 이상만 가입 가능합니다.');
        return false;
      }
    }

    // 강화된 비밀번호 검증 (회원가입만)
    if (!formData.password || formData.password.length < 10) {
      setError('비밀번호는 최소 10자 이상이어야 합니다.');
      return false;
    }

    if (!/[A-Z]/.test(formData.password)) {
      setError('비밀번호에 영어 대문자가 1개 이상 포함되어야 합니다.');
      return false;
    }

    if (!/[!@#$%^&*(),.?":{}|<>]/.test(formData.password)) {
      setError('비밀번호에 특수문자(!@#$%^&*(),.?\":{}|<>)가 1개 이상 포함되어야 합니다.');
      return false;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      if (!isLogin) {
        // 회원가입 로직
        if (!validateSignupForm()) {
          setLoading(false);
          return;
        }

        // API 요청 데이터 준비
        const requestData = {
          username: formData.username,
          email: formData.email,
          password: formData.password
        };

        // 선택사항들은 값이 있을 때만 포함
        if (formData.nickname) requestData.nickname = formData.nickname;
        if (formData.birth_year) requestData.birth_year = parseInt(formData.birth_year);
        if (formData.gender) requestData.gender = formData.gender;
        if (formData.interests.length > 0) requestData.interests = formData.interests;
        if (formData.need) requestData.need = formData.need;

        const response = await axios.post(
          `${API_BASE_URL}/auth/register`,
          requestData,
          {
            headers: {
              'Content-Type': 'application/json',
            },
          }
        );

        setSuccess('회원가입이 완료되었습니다! 이제 로그인할 수 있습니다.');
        setFormData({
          email: '',
          password: '',
          username: '',
          confirmPassword: '',
          nickname: '',
          birth_year: '',
          gender: '',
          interests: [],
          need: ''
        });
        setIsLogin(true); // 회원가입 후 로그인 모드로 전환

      } else {
        // 로그인 로직
        if (!validateLoginForm()) {
          setLoading(false);
          return;
        }

        const formDataObj = new FormData();
        formDataObj.append('username', formData.email); // 이메일을 username 필드에 전송
        formDataObj.append('password', formData.password);

        const response = await axios.post(
          `${API_BASE_URL}/auth/login`,
          formDataObj,
          {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
          }
        );

        const { access_token, user: userData } = response.data;

        localStorage.setItem('access_token', access_token);
        setToken(access_token);
        setUser(userData);

        setSuccess('로그인 성공! 홈페이지로 이동합니다...');

        setTimeout(() => {
          navigate('/');
        }, 1500);
      }

    } catch (err) {
      console.error('요청 오류:', err);
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError(isLogin ? '로그인에 실패했습니다.' : '회원가입에 실패했습니다.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    setToken('');
    setUser(null);
    setFormData({
      email: '',
      password: '',
      username: '',
      confirmPassword: '',
      nickname: '',
      birth_year: '',
      gender: '',
      interests: [],
      need: ''
    });
    setSuccess('');
    setError('');
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setError('');
    setSuccess('');
    setFormData({
      email: '',
      password: '',
      username: '',
      confirmPassword: '',
      nickname: '',
      birth_year: '',
      gender: '',
      interests: [],
      need: ''
    });
  };

  // 이미 로그인된 상태라면 사용자 정보 표시
  if (token && user) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="bg-white dark:bg-gray-800 py-8 px-4 shadow sm:rounded-lg sm:px-10">
            <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-white mb-6">
              로그인 완료
            </h2>
            <div className="text-center space-y-4">
              <p className="text-gray-600 dark:text-gray-300">
                환영합니다, <span className="font-semibold">{user.username}</span>님!
              </p>
              <div className="space-y-2">
                <button
                  onClick={() => navigate('/')}
                  className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700"
                >
                  홈으로 이동
                </button>
                <button
                  onClick={handleLogout}
                  className="w-full bg-gray-600 text-white py-2 px-4 rounded-md hover:bg-gray-700"
                >
                  로그아웃
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900 dark:text-white">
          {isLogin ? '로그인' : '회원가입'}
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
          {isLogin ? '계정에 로그인하세요' : '새 계정을 만드세요'}
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white dark:bg-gray-800 py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {/* 오류 메시지 */}
            {error && (
              <div className="bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-700 text-red-600 dark:text-red-200 px-4 py-3 rounded">
                {error}
              </div>
            )}

            {/* 성공 메시지 */}
            {success && (
              <div className="bg-green-50 dark:bg-green-900 border border-green-200 dark:border-green-700 text-green-600 dark:text-green-200 px-4 py-3 rounded">
                {success}
              </div>
            )}

            {/* 이메일 (필수) */}
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
                autoComplete="email"
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 dark:bg-gray-700 dark:text-white"
                placeholder="example@domain.com"
              />
              {!isLogin && (
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  로그인시 이메일로도 로그인 가능합니다
                </p>
              )}
            </div>

            {/* 회원가입시에만 표시되는 사용자명 필드 */}
            {!isLogin && (
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  사용자명 *
                </label>
                <input
                  type="text"
                  id="username"
                  name="username"
                  value={formData.username}
                  onChange={handleInputChange}
                  required
                  autoComplete="username"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 dark:bg-gray-700 dark:text-white"
                  placeholder="영문, 숫자, 언더스코어만 사용"
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  3자 이상, 영문/숫자/언더스코어(_)만 사용 가능
                </p>
              </div>
            )}

            {/* 회원가입시에만 표시되는 추가 필드들 */}
            {!isLogin && (
              <>
                {/* 닉네임 (선택) */}
                <div>
                  <label htmlFor="nickname" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    닉네임
                  </label>
                  <input
                    type="text"
                    id="nickname"
                    name="nickname"
                    value={formData.nickname}
                    onChange={handleInputChange}
                    autoComplete="nickname"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 dark:bg-gray-700 dark:text-white"
                    placeholder="표시될 이름 (선택사항)"
                  />
                </div>

                {/* 출생년도 (선택) */}
                <div>
                  <label htmlFor="birth_year" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    출생년도
                  </label>
                  <input
                    type="number"
                    id="birth_year"
                    name="birth_year"
                    value={formData.birth_year}
                    onChange={handleInputChange}
                    min="1900"
                    max={new Date().getFullYear()}
                    autoComplete="bday-year"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 dark:bg-gray-700 dark:text-white"
                    placeholder="예: 1990"
                  />
                </div>

                {/* 성별 (선택) */}
                <div>
                  <label htmlFor="gender" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    성별
                  </label>
                  <select
                    id="gender"
                    name="gender"
                    value={formData.gender}
                    onChange={handleInputChange}
                    autoComplete="sex"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="">선택하지 않음</option>
                    <option value="남성">남성</option>
                    <option value="여성">여성</option>
                    <option value="선택 안함">선택 안함</option>
                  </select>
                </div>

                {/* 관심사 (선택) */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    관심사 (최대 10개)
                  </label>
                  <div className="grid grid-cols-2 gap-2 max-h-32 overflow-y-auto">
                    {interestOptions.map((interest, index) => (
                      <label key={interest} htmlFor={`interest-${index}`} className="flex items-center text-xs">
                        <input
                          type="checkbox"
                          id={`interest-${index}`}
                          checked={formData.interests.includes(interest)}
                          onChange={() => handleInterestChange(interest)}
                          className="rounded border-gray-300 text-green-600 shadow-sm focus:border-green-500 focus:ring focus:ring-green-500 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-gray-700 dark:text-gray-300">{interest}</span>
                      </label>
                    ))}
                  </div>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    선택한 관심사: {formData.interests.length}/10
                  </p>
                </div>

                {/* 필요사항 (선택) */}
                <div>
                  <label htmlFor="need" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    필요사항
                  </label>
                  <select
                    id="need"
                    name="need"
                    value={formData.need}
                    onChange={handleInputChange}
                    autoComplete="off"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="">선택하지 않음</option>
                    {needOptions.map((need) => (
                      <option key={need} value={need}>{need}</option>
                    ))}
                  </select>
                </div>
              </>
            )}

            {/* 비밀번호 */}
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
                autoComplete={isLogin ? "current-password" : "new-password"}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 dark:bg-gray-700 dark:text-white"
                placeholder={isLogin ? "비밀번호" : "10자 이상, 대문자+특수문자 포함"}
              />
              {!isLogin && (
                <div className="mt-2 text-xs text-gray-600 dark:text-gray-400">
                  <p className="font-medium mb-1">비밀번호 요구사항:</p>
                  <ul className="list-disc list-inside space-y-1">
                    <li>최소 10자 이상</li>
                    <li>영어 대문자 1개 이상</li>
                    <li>특수문자 1개 이상 (!@#$%^&*(),.?\":{ }|&lt;&gt;)</li>
                  </ul>
                </div>
              )}
            </div>

            {/* 비밀번호 확인 (회원가입시만) */}
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
                  autoComplete="new-password"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-green-500 focus:border-green-500 dark:bg-gray-700 dark:text-white"
                  placeholder="비밀번호 다시 입력"
                />
              </div>
            )}

            {/* 제출 버튼 */}
            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (isLogin ? '로그인 중...' : '가입 중...') : (isLogin ? '로그인' : '회원가입')}
              </button>
            </div>

            {/* 모드 전환 버튼 */}
            <div className="text-center">
              <button
                type="button"
                onClick={toggleMode}
                className="text-sm text-green-600 hover:text-green-500 dark:text-green-400 dark:hover:text-green-300"
              >
                {isLogin
                  ? '계정이 없으신가요? 회원가입하기'
                  : '이미 계정이 있으신가요? 로그인하기'
                }
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
