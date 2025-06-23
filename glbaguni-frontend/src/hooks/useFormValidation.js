import { useState } from 'react';

export const useFormValidation = () => {
  const [validationErrors, setValidationErrors] = useState({});

  // Validation functions
  const validateEmail = (email) => {
    if (!email || !email.trim()) {
      return '이메일 주소를 입력해주세요';
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email) ? '' : '유효한 이메일 주소를 입력해주세요';
  };

  const validateUrls = (urlString) => {
    if (!urlString || !urlString.trim()) return '';
    
    const urls = urlString.split('\n').map(url => url.trim()).filter(url => url);
    const urlRegex = /^https?:\/\/.+/;
    
    for (const url of urls) {
      if (!urlRegex.test(url)) {
        return 'URL은 http:// 또는 https://로 시작해야 합니다';
      }
    }
    return '';
  };

  const validateUrlFields = (rssUrls, articleUrls) => {
    const hasRssUrls = rssUrls && rssUrls.trim().length > 0;
    const hasArticleUrls = articleUrls && articleUrls.trim().length > 0;
    
    if (!hasRssUrls && !hasArticleUrls) {
      return 'RSS URL 또는 기사 URL을 최소 하나 이상 입력해주세요';
    }
    return '';
  };

  const validateMaxArticles = (maxArticles) => {
    const num = parseInt(maxArticles);
    if (isNaN(num) || num < 1 || num > 50) {
      return '1~50 사이의 숫자를 입력해주세요';
    }
    return '';
  };

  // Validate entire form
  const validateForm = (formData) => {
    if (!formData) {
      setValidationErrors({});
      return false;
    }

    const newErrors = {};

    // Validate email
    const emailError = validateEmail(formData.recipientEmail);
    if (emailError) newErrors.recipientEmail = emailError;

    // Validate RSS URLs if provided
    if (formData.rssUrls) {
      const rssUrlError = validateUrls(formData.rssUrls);
      if (rssUrlError) newErrors.rssUrls = rssUrlError;
    }

    // Validate Article URLs if provided
    if (formData.articleUrls) {
      const articleUrlError = validateUrls(formData.articleUrls);
      if (articleUrlError) newErrors.articleUrls = articleUrlError;
    }

    // Validate that at least one URL field has content
    const urlFieldError = validateUrlFields(formData.rssUrls, formData.articleUrls);
    if (urlFieldError) {
      if (!newErrors.rssUrls && !formData.rssUrls) newErrors.rssUrls = urlFieldError;
      if (!newErrors.articleUrls && !formData.articleUrls) newErrors.articleUrls = urlFieldError;
    }

    // Validate max articles
    if (formData.maxArticles) {
      const maxArticlesError = validateMaxArticles(formData.maxArticles);
      if (maxArticlesError) newErrors.maxArticles = maxArticlesError;
    }

    setValidationErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Field-specific validation for onBlur events
  const validateField = (fieldName, value, formData = {}) => {
    let error = '';

    switch (fieldName) {
      case 'recipientEmail':
        error = validateEmail(value);
        break;
      case 'rssUrls':
        error = validateUrls(value);
        if (!error) {
          // Check if we need at least one URL
          const urlFieldError = validateUrlFields(value, formData.articleUrls);
          if (urlFieldError && !formData.articleUrls) error = urlFieldError;
        }
        break;
      case 'articleUrls':
        error = validateUrls(value);
        if (!error) {
          // Check if we need at least one URL
          const urlFieldError = validateUrlFields(formData.rssUrls, value);
          if (urlFieldError && !formData.rssUrls) error = urlFieldError;
        }
        break;
      case 'maxArticles':
        error = validateMaxArticles(value);
        break;
      default:
        break;
    }

    setValidationErrors(prev => ({
      ...prev,
      [fieldName]: error
    }));

    return error === '';
  };

  // Get CSS classes for input fields
  const getInputClasses = (fieldName, baseClasses) => {
    const hasError = validationErrors[fieldName];
    const errorClasses = hasError 
      ? 'border-red-500 dark:border-red-500 focus:ring-red-500 dark:focus:ring-red-500' 
      : 'border-gray-300 dark:border-gray-600 focus:ring-blue-500 dark:focus:ring-blue-600';
    
    return `${baseClasses} ${errorClasses}`;
  };

  // Clear all validation errors
  const clearErrors = () => {
    setValidationErrors({});
  };

  return {
    validationErrors,
    validateForm,
    validateField,
    getInputClasses,
    clearErrors
  };
}; 