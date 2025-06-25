import { useState, useCallback } from 'react';

export const useToast = () => {
    const [toasts, setToasts] = useState([]);

    const addToast = useCallback((message, type = 'info', options = {}) => {
        const id = Date.now() + Math.random();
        const toast = {
            id,
            message,
            type,
            title: options.title,
            duration: options.duration !== undefined ? options.duration : 5000,
            ...options
        };

        setToasts(prev => [...prev, toast]);
        return id;
    }, []);

    const removeToast = useCallback((id) => {
        setToasts(prev => prev.filter(toast => toast.id !== id));
    }, []);

    const clearAllToasts = useCallback(() => {
        setToasts([]);
    }, []);

    // 편의 함수들
    const showSuccess = useCallback((message, options = {}) => {
        return addToast(message, 'success', options);
    }, [addToast]);

    const showError = useCallback((message, options = {}) => {
        return addToast(message, 'error', { duration: 7000, ...options });
    }, [addToast]);

    const showWarning = useCallback((message, options = {}) => {
        return addToast(message, 'warning', options);
    }, [addToast]);

    const showInfo = useCallback((message, options = {}) => {
        return addToast(message, 'info', options);
    }, [addToast]);

    return {
        toasts,
        addToast,
        removeToast,
        clearAllToasts,
        showSuccess,
        showError,
        showWarning,
        showInfo
    };
}; 