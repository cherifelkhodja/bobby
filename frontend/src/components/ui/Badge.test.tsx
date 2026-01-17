import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Badge } from './Badge';

describe('Badge', () => {
  describe('with status', () => {
    it('should render pending status', () => {
      render(<Badge status="pending" />);
      expect(screen.getByText('En attente')).toBeInTheDocument();
    });

    it('should render in_review status', () => {
      render(<Badge status="in_review" />);
      expect(screen.getByText("En cours d'examen")).toBeInTheDocument();
    });

    it('should render interview status', () => {
      render(<Badge status="interview" />);
      expect(screen.getByText('En entretien')).toBeInTheDocument();
    });

    it('should render accepted status', () => {
      render(<Badge status="accepted" />);
      expect(screen.getByText('Accepté')).toBeInTheDocument();
    });

    it('should render rejected status', () => {
      render(<Badge status="rejected" />);
      expect(screen.getByText('Refusé')).toBeInTheDocument();
    });
  });

  describe('with variant', () => {
    it('should render default variant', () => {
      render(<Badge variant="default">Default</Badge>);
      expect(screen.getByText('Default')).toBeInTheDocument();
    });

    it('should render primary variant', () => {
      render(<Badge variant="primary">Primary</Badge>);
      expect(screen.getByText('Primary')).toBeInTheDocument();
    });

    it('should render success variant', () => {
      render(<Badge variant="success">Success</Badge>);
      expect(screen.getByText('Success')).toBeInTheDocument();
    });

    it('should render warning variant', () => {
      render(<Badge variant="warning">Warning</Badge>);
      expect(screen.getByText('Warning')).toBeInTheDocument();
    });

    it('should render error variant', () => {
      render(<Badge variant="error">Error</Badge>);
      expect(screen.getByText('Error')).toBeInTheDocument();
    });
  });

  describe('with children', () => {
    it('should render children when provided', () => {
      render(<Badge variant="default">Custom Content</Badge>);
      expect(screen.getByText('Custom Content')).toBeInTheDocument();
    });

    it('should prefer children over status label', () => {
      render(<Badge status="pending">Custom Label</Badge>);
      expect(screen.getByText('Custom Label')).toBeInTheDocument();
      expect(screen.queryByText('En attente')).not.toBeInTheDocument();
    });
  });

  describe('styling', () => {
    it('should have base styling classes', () => {
      render(<Badge variant="default">Test</Badge>);
      const badge = screen.getByText('Test');
      expect(badge).toHaveClass('inline-flex');
      expect(badge).toHaveClass('items-center');
      expect(badge).toHaveClass('rounded-full');
      expect(badge).toHaveClass('text-xs');
      expect(badge).toHaveClass('font-medium');
    });
  });
});
