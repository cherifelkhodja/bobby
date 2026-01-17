import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Card, CardHeader } from './Card';

describe('Card', () => {
  it('should render children', () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    render(<Card className="custom-class">Content</Card>);
    // The Card component renders a div with children inside
    // getByText returns the element containing the text
    const card = screen.getByText('Content').closest('div');
    expect(card).toHaveClass('custom-class');
  });

  describe('padding', () => {
    it('should apply no padding', () => {
      render(<Card padding="none">Content</Card>);
      const card = screen.getByText('Content');
      expect(card).not.toHaveClass('p-4');
      expect(card).not.toHaveClass('p-6');
      expect(card).not.toHaveClass('p-8');
    });

    it('should apply small padding', () => {
      render(<Card padding="sm">Content</Card>);
      const card = screen.getByText('Content');
      expect(card).toHaveClass('p-4');
    });

    it('should apply medium padding by default', () => {
      render(<Card>Content</Card>);
      const card = screen.getByText('Content');
      expect(card).toHaveClass('p-6');
    });

    it('should apply large padding', () => {
      render(<Card padding="lg">Content</Card>);
      const card = screen.getByText('Content');
      expect(card).toHaveClass('p-8');
    });
  });

  describe('clickable card', () => {
    it('should call onClick when clicked', () => {
      const onClick = vi.fn();
      render(<Card onClick={onClick}>Clickable</Card>);

      fireEvent.click(screen.getByText('Clickable'));
      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('should have button role when clickable', () => {
      const onClick = vi.fn();
      render(<Card onClick={onClick}>Clickable</Card>);

      const card = screen.getByRole('button');
      expect(card).toBeInTheDocument();
    });

    it('should have tabIndex when clickable', () => {
      const onClick = vi.fn();
      render(<Card onClick={onClick}>Clickable</Card>);

      const card = screen.getByRole('button');
      expect(card).toHaveAttribute('tabIndex', '0');
    });

    it('should trigger onClick on Enter key', () => {
      const onClick = vi.fn();
      render(<Card onClick={onClick}>Clickable</Card>);

      const card = screen.getByRole('button');
      fireEvent.keyDown(card, { key: 'Enter' });
      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('should not trigger onClick on other keys', () => {
      const onClick = vi.fn();
      render(<Card onClick={onClick}>Clickable</Card>);

      const card = screen.getByRole('button');
      fireEvent.keyDown(card, { key: 'Space' });
      expect(onClick).not.toHaveBeenCalled();
    });

    it('should not have role when not clickable', () => {
      render(<Card>Not clickable</Card>);
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
  });
});

describe('CardHeader', () => {
  it('should render title', () => {
    render(<CardHeader title="Card Title" />);
    expect(screen.getByText('Card Title')).toBeInTheDocument();
  });

  it('should render subtitle when provided', () => {
    render(<CardHeader title="Title" subtitle="Subtitle text" />);
    expect(screen.getByText('Subtitle text')).toBeInTheDocument();
  });

  it('should render action when provided', () => {
    render(
      <CardHeader
        title="Title"
        action={<button>Action</button>}
      />
    );
    expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
  });

  it('should apply heading styling', () => {
    render(<CardHeader title="Title" />);
    const title = screen.getByText('Title');
    expect(title.tagName).toBe('H3');
    expect(title).toHaveClass('text-lg', 'font-semibold');
  });
});
