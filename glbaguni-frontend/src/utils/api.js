import axios from 'axios';

// API Base URL
const API_BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8003';

// 환경변수 검증 (선택사항으로 변경)
if (!import.meta.env.VITE_API_BASE) {
  console.info('ℹ️ VITE_API_BASE 환경변수가 설정되지 않아 기본값을 사용합니다:', API_BASE_URL);
}

// Axios 인스턴스 생성
const api = axios.create({
  baseURL: API_BASE_URL,
});

// 요청 인터셉터: 토큰을 자동으로 헤더에 추가
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터: 토큰 만료 처리
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // 토큰이 만료되었거나 유효하지 않은 경우
      localStorage.removeItem('access_token');
      localStorage.removeItem('token_type');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API 함수들
export const authAPI = {
  // 회원가입
  register: async (username, password) => {
    const response = await api.post('/auth/register', {
      username,
      password
    });
    return response.data;
  },

  // 로그인
  login: async (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const response = await api.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  },

  // 현재 사용자 정보 조회
  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

// 뉴스 소스 API
export const sourcesAPI = {
  // 모든 뉴스 소스 조회
  getAllSources: async () => {
    const response = await api.get('/sources/');
    return response.data;
  },

  // 카테고리별 뉴스 소스 조회
  getSourcesByCategory: async (category) => {
    const response = await api.get(`/sources/?category=${category}`);
    return response.data;
  },

  // 사용 가능한 카테고리 목록 조회
  getCategories: async () => {
    const response = await api.get('/sources/categories');
    return response.data;
  },

  // 뉴스 소스 구독
  subscribe: async (user_id, name, rss_url) => {
    const response = await api.post('/subscribe', {
      user_id,
      name,
      rss_url
    });
    return response.data;
  },
};

// 피드백 API
export const feedbackAPI = {
  // 피드백 제출
  submitFeedback: async (feedbackData) => {
    const response = await api.post('/feedback', feedbackData);
    return response.data;
  },

  // 피드백 통계 조회
  getFeedbackStats: async (days = 30) => {
    const response = await api.get(`/feedback/stats?days=${days}`);
    return response.data;
  },
};

export default api;
