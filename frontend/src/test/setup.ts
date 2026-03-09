import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// ── jsdom 환경 polyfills ────────────────────────────────

// window.matchMedia — Ant Design 내부에서 사용
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// ResizeObserver — Ant Design Table/Layout 등에서 사용
class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
vi.stubGlobal('ResizeObserver', MockResizeObserver);

// IntersectionObserver — 가상 스크롤, lazy loading 등
class MockIntersectionObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
  readonly root = null;
  readonly rootMargin = '';
  readonly thresholds: readonly number[] = [];
  takeRecords = vi.fn().mockReturnValue([]);
}
vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);

// getComputedStyle — Ant Design CSS 계산에서 사용
const originalGetComputedStyle = window.getComputedStyle;
window.getComputedStyle = (elt: Element, pseudoElt?: string | null) => {
  try {
    return originalGetComputedStyle(elt, pseudoElt);
  } catch {
    return {} as CSSStyleDeclaration;
  }
};

// Ant Design 경고 억제 (테스트 출력 깨끗하게)
const originalConsoleError = console.error;
console.error = (...args: unknown[]) => {
  const message = typeof args[0] === 'string' ? args[0] : '';
  // Ant Design 내부 경고 억제
  if (
    message.includes('Warning:') ||
    message.includes('validateDOMNesting') ||
    message.includes('act()')
  ) {
    return;
  }
  originalConsoleError(...args);
};
