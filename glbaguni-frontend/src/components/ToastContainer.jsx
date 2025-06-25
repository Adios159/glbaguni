import React from 'react';
import Toast from './Toast';

const ToastContainer = ({ toasts, removeToast }) => {
    return (
        <div className="fixed top-4 right-4 z-50 space-y-2">
            {toasts.map((toast, index) => (
                <Toast
                    key={toast.id}
                    id={index}
                    type={toast.type}
                    title={toast.title}
                    message={toast.message}
                    duration={toast.duration}
                    onClose={() => removeToast(toast.id)}
                />
            ))}
        </div>
    );
};

export default ToastContainer; 