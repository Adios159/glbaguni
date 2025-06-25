import { useState, useEffect, useRef } from 'react';

export const useSwipe = (onSwipeLeft, onSwipeRight, onSwipeUp, onSwipeDown) => {
    const [isSwiping, setIsSwiping] = useState(false);
    const touchRef = useRef({
        startX: 0,
        startY: 0,
        startTime: 0,
        isTouch: false,
    });

    const minSwipeDistance = 50; // 최소 스와이프 거리
    const maxSwipeTime = 300; // 최대 스와이프 시간 (ms)
    const maxVerticalMovement = 100; // 수직 이동 허용 범위

    const handleTouchStart = (e) => {
        setIsSwiping(true);
        const touch = e.touches[0];
        touchRef.current = {
            startX: touch.clientX,
            startY: touch.clientY,
            startTime: Date.now(),
            isTouch: true,
        };
    };

    const handleTouchMove = (e) => {
        if (!touchRef.current.isTouch) return;

        // 스크롤 방지 (옵션)
        e.preventDefault();
    };

    const handleTouchEnd = (e) => {
        if (!touchRef.current.isTouch) {
            setIsSwiping(false);
            return;
        }

        const touch = e.changedTouches[0];
        const endX = touch.clientX;
        const endY = touch.clientY;
        const endTime = Date.now();

        const deltaX = endX - touchRef.current.startX;
        const deltaY = endY - touchRef.current.startY;
        const deltaTime = endTime - touchRef.current.startTime;

        // 스와이프 조건 검사
        const isValidSwipe =
            Math.abs(deltaX) > minSwipeDistance &&
            deltaTime < maxSwipeTime;

        const isHorizontalSwipe = Math.abs(deltaX) > Math.abs(deltaY);
        const isVerticalSwipe = Math.abs(deltaY) > Math.abs(deltaX);

        if (isValidSwipe && isHorizontalSwipe) {
            if (Math.abs(deltaY) < maxVerticalMovement) {
                if (deltaX > 0) {
                    onSwipeRight && onSwipeRight();
                } else {
                    onSwipeLeft && onSwipeLeft();
                }
            }
        } else if (Math.abs(deltaY) > minSwipeDistance && deltaTime < maxSwipeTime && isVerticalSwipe) {
            if (deltaY > 0) {
                onSwipeDown && onSwipeDown();
            } else {
                onSwipeUp && onSwipeUp();
            }
        }

        // 초기화
        touchRef.current.isTouch = false;
        setIsSwiping(false);
    };

    return {
        onTouchStart: handleTouchStart,
        onTouchMove: handleTouchMove,
        onTouchEnd: handleTouchEnd,
        isSwiping,
    };
};

// 모바일 디바이스 감지 훅
export const useIsMobile = () => {
    const [isMobile, setIsMobile] = useState(false);

    useEffect(() => {
        const checkIsMobile = () => {
            const userAgent = navigator.userAgent || navigator.vendor || window.opera;
            const isMobileDevice = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
            const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
            const isSmallScreen = window.innerWidth < 768;

            setIsMobile(isMobileDevice || (isTouchDevice && isSmallScreen));
        };

        checkIsMobile();
        window.addEventListener('resize', checkIsMobile);

        return () => window.removeEventListener('resize', checkIsMobile);
    }, []);

    return isMobile;
};

// 터치 제스처 설정 훅
export const useTouchGestures = () => {
    const [gestures, setGestures] = useState({
        pinchToZoom: false,
        doubleTapToZoom: false,
        pullToRefresh: false,
    });

    useEffect(() => {
        // 기본 터치 제스처 비활성화
        const disableDefaults = (e) => {
            // 핀치 줌 방지
            if (e.touches && e.touches.length > 1) {
                e.preventDefault();
            }
        };

        const disableDoubleTap = (e) => {
            // 더블탭 줌 방지
            e.preventDefault();
        };

        if (!gestures.pinchToZoom) {
            document.addEventListener('touchmove', disableDefaults, { passive: false });
        }

        if (!gestures.doubleTapToZoom) {
            document.addEventListener('touchend', disableDoubleTap, { passive: false });
        }

        return () => {
            document.removeEventListener('touchmove', disableDefaults);
            document.removeEventListener('touchend', disableDoubleTap);
        };
    }, [gestures]);

    return { gestures, setGestures };
};

// 풀 투 리프레시 훅
export const usePullToRefresh = (onRefresh, threshold = 100) => {
    const [isPulling, setIsPulling] = useState(false);
    const [pullDistance, setPullDistance] = useState(0);
    const startY = useRef(0);
    const isRefreshing = useRef(false);

    const handleTouchStart = (e) => {
        if (window.scrollY === 0 && !isRefreshing.current) {
            startY.current = e.touches[0].clientY;
        }
    };

    const handleTouchMove = (e) => {
        if (startY.current === 0 || isRefreshing.current) return;

        const currentY = e.touches[0].clientY;
        const distance = currentY - startY.current;

        if (distance > 0 && window.scrollY === 0) {
            e.preventDefault();
            setPullDistance(Math.min(distance, threshold * 1.5));
            setIsPulling(distance > threshold / 2);
        }
    };

    const handleTouchEnd = () => {
        if (pullDistance > threshold && !isRefreshing.current) {
            isRefreshing.current = true;
            onRefresh && onRefresh();

            setTimeout(() => {
                isRefreshing.current = false;
                setPullDistance(0);
                setIsPulling(false);
                startY.current = 0;
            }, 1000);
        } else {
            setPullDistance(0);
            setIsPulling(false);
            startY.current = 0;
        }
    };

    return {
        onTouchStart: handleTouchStart,
        onTouchMove: handleTouchMove,
        onTouchEnd: handleTouchEnd,
        isPulling,
        pullDistance,
        isRefreshing: isRefreshing.current,
    };
}; 