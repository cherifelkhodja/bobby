import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Spinner, PageSpinner } from './Spinner';

describe('Spinner', () => {
  it('should render spinner', () => {
    const { container } = render(<Spinner />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('should have animation class', () => {
    const { container } = render(<Spinner />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveClass('animate-spin');
  });

  describe('sizes', () => {
    it('should render small size', () => {
      const { container } = render(<Spinner size="sm" />);
      const svg = container.querySelector('svg');
      expect(svg).toHaveClass('h-4', 'w-4');
    });

    it('should render medium size by default', () => {
      const { container } = render(<Spinner />);
      const svg = container.querySelector('svg');
      expect(svg).toHaveClass('h-6', 'w-6');
    });

    it('should render large size', () => {
      const { container } = render(<Spinner size="lg" />);
      const svg = container.querySelector('svg');
      expect(svg).toHaveClass('h-8', 'w-8');
    });
  });

  it('should apply custom className', () => {
    const { container } = render(<Spinner className="custom-class" />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveClass('custom-class');
  });
});

describe('PageSpinner', () => {
  it('should render centered spinner', () => {
    const { container } = render(<PageSpinner />);

    // Should have centering container
    const centerContainer = container.firstChild;
    expect(centerContainer).toHaveClass('flex', 'items-center', 'justify-center');
  });

  it('should render large spinner', () => {
    const { container } = render(<PageSpinner />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveClass('h-8', 'w-8');
  });
});
