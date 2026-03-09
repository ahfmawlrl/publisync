import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import PageHeader from './PageHeader';

describe('PageHeader', () => {
  it('should render title', () => {
    render(<PageHeader title="테스트 제목" />);
    expect(screen.getByText('테스트 제목')).toBeInTheDocument();
  });

  it('should render subtitle when provided', () => {
    render(<PageHeader title="제목" subtitle="부제목입니다" />);
    expect(screen.getByText('제목')).toBeInTheDocument();
    expect(screen.getByText('부제목입니다')).toBeInTheDocument();
  });

  it('should not render subtitle when not provided', () => {
    const { container } = render(<PageHeader title="제목만" />);
    // Only the title element, no secondary text
    const secondaryTexts = container.querySelectorAll('.ant-typography-secondary');
    expect(secondaryTexts).toHaveLength(0);
  });
});
