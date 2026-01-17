import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Pagination, SimplePagination } from './Pagination';

describe('Pagination', () => {
  const defaultProps = {
    page: 1,
    total: 100,
    pageSize: 10,
    onPageChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render pagination', () => {
    render(<Pagination {...defaultProps} />);
    expect(screen.getByText('Page 1 sur 10')).toBeInTheDocument();
  });

  it('should show total results', () => {
    render(<Pagination {...defaultProps} />);
    expect(screen.getByText('(100 résultats)')).toBeInTheDocument();
  });

  it('should show singular for 1 result', () => {
    render(<Pagination {...defaultProps} total={1} />);
    expect(screen.getByText('(1 résultat)')).toBeInTheDocument();
  });

  describe('navigation', () => {
    it('should disable previous buttons on first page', () => {
      render(<Pagination {...defaultProps} page={1} />);

      const firstPageButton = screen.getByTitle('Première page');
      const prevButton = screen.getByTitle('Page précédente');

      expect(firstPageButton).toBeDisabled();
      expect(prevButton).toBeDisabled();
    });

    it('should disable next buttons on last page', () => {
      render(<Pagination {...defaultProps} page={10} />);

      const lastPageButton = screen.getByTitle('Dernière page');
      const nextButton = screen.getByTitle('Page suivante');

      expect(lastPageButton).toBeDisabled();
      expect(nextButton).toBeDisabled();
    });

    it('should call onPageChange when clicking next', () => {
      const onPageChange = vi.fn();
      render(<Pagination {...defaultProps} page={5} onPageChange={onPageChange} />);

      fireEvent.click(screen.getByTitle('Page suivante'));
      expect(onPageChange).toHaveBeenCalledWith(6);
    });

    it('should call onPageChange when clicking previous', () => {
      const onPageChange = vi.fn();
      render(<Pagination {...defaultProps} page={5} onPageChange={onPageChange} />);

      fireEvent.click(screen.getByTitle('Page précédente'));
      expect(onPageChange).toHaveBeenCalledWith(4);
    });

    it('should call onPageChange when clicking first page', () => {
      const onPageChange = vi.fn();
      render(<Pagination {...defaultProps} page={5} onPageChange={onPageChange} />);

      fireEvent.click(screen.getByTitle('Première page'));
      expect(onPageChange).toHaveBeenCalledWith(1);
    });

    it('should call onPageChange when clicking last page', () => {
      const onPageChange = vi.fn();
      render(<Pagination {...defaultProps} page={5} onPageChange={onPageChange} />);

      fireEvent.click(screen.getByTitle('Dernière page'));
      expect(onPageChange).toHaveBeenCalledWith(10);
    });
  });

  describe('options', () => {
    it('should hide first/last buttons when showFirstLast is false', () => {
      render(<Pagination {...defaultProps} showFirstLast={false} />);

      expect(screen.queryByTitle('Première page')).not.toBeInTheDocument();
      expect(screen.queryByTitle('Dernière page')).not.toBeInTheDocument();
    });

    it('should hide page info when showPageInfo is false', () => {
      render(<Pagination {...defaultProps} showPageInfo={false} />);

      expect(screen.queryByText('Page 1 sur 10')).not.toBeInTheDocument();
    });

    it('should return null when only one page and no page info', () => {
      const { container } = render(
        <Pagination {...defaultProps} total={5} showPageInfo={false} />
      );

      expect(container.firstChild).toBeNull();
    });
  });

  it('should apply custom className', () => {
    const { container } = render(
      <Pagination {...defaultProps} className="custom-class" />
    );

    expect(container.firstChild).toHaveClass('custom-class');
  });
});

describe('SimplePagination', () => {
  const defaultProps = {
    page: 1,
    totalPages: 5,
    onPageChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render simple pagination', () => {
    render(<SimplePagination {...defaultProps} />);
    expect(screen.getByText('Page 1 / 5')).toBeInTheDocument();
  });

  it('should return null when only one page', () => {
    const { container } = render(
      <SimplePagination {...defaultProps} totalPages={1} />
    );

    expect(container.firstChild).toBeNull();
  });

  it('should disable previous on first page', () => {
    render(<SimplePagination {...defaultProps} page={1} />);
    expect(screen.getByText('Précédent')).toBeDisabled();
  });

  it('should disable next on last page', () => {
    render(<SimplePagination {...defaultProps} page={5} />);
    expect(screen.getByText('Suivant')).toBeDisabled();
  });

  it('should call onPageChange when clicking buttons', () => {
    const onPageChange = vi.fn();
    render(<SimplePagination {...defaultProps} page={3} onPageChange={onPageChange} />);

    fireEvent.click(screen.getByText('Suivant'));
    expect(onPageChange).toHaveBeenCalledWith(4);

    fireEvent.click(screen.getByText('Précédent'));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });
});
