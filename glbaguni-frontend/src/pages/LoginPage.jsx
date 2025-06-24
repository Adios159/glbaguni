import React from 'react';
import LoginForm from '../components/LoginForm';

const LoginPage = () => {
  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold text-center mb-8 text-gray-800">
          글바구니 로그인
        </h1>
        <LoginForm />
        
        {/* 테스트용 정보 */}
        <div className="max-w-md mx-auto mt-8 p-4 bg-blue-50 border border-blue-200 rounded-md">
          <h3 className="text-sm font-semibold text-blue-800 mb-2">테스트 정보:</h3>
          <p className="text-xs text-blue-700">
            먼저 백엔드 서버에서 회원가입을 진행하거나<br/>
            POST /auth/register API를 사용하여 계정을 생성하세요.
          </p>
          <div className="mt-2 text-xs text-blue-600">
            <p><strong>백엔드 URL:</strong> http://localhost:8001</p>
            <p><strong>회원가입:</strong> POST /auth/register</p>
            <p><strong>로그인:</strong> POST /auth/login</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
