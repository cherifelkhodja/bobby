import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SearchInput, InlineSearchInput } from './SearchInput';

describe('SearchInput', () => {
  const defaultProps = {
    value: '',
    onChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render search input', () => {
    render(<SearchInput {...defaultProps} />);
    expect(screen.getByPlaceholderText('Rechercher...')).toBeInTheDocument();
  });

  it('should render custom placeholder', () => {
    render(<SearchInput {...defaultProps} placeholder="Search users..." />);
    expect(screen.getByPlaceholderText('Search users...')).toBeInTheDocument();
  });

  it('should call onChange when typing', () => {
    const onChange = vi.fn();
    render(<SearchInput {...defaultProps} onChange={onChange} />);

    const input = screen.getByPlaceholderText('Rechercher...');
    fireEvent.change(input, { target: { value: 'test' } });

    expect(onChange).toHaveBeenCalled();
  });

  describe('clear button', () => {
    it('should not show clear button when value is empty', () => {
      render(<SearchInput {...defaultProps} value="" />);
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });

    it('should show clear button when value is present', () => {
      render(<SearchInput {...defaultProps} value="test" />);
      // The clear button doesn't have explicit text, but is a button
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('should call onChange with empty string when clear is clicked', () => {
      const onChange = vi.fn();
      render(<SearchInput {...defaultProps} value="test" onChange={onChange} />);

      // Find the clear button (X icon button)
      const clearButton = screen.getByRole('button');
      fireEvent.click(clearButton);

      expect(onChange).toHaveBeenCalledWith('');
    });

    it('should not show clear button when showClearButton is false', () => {
      render(<SearchInput {...defaultProps} value="test" showClearButton={false} />);
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
  });

  describe('submit button', () => {
    it('should not show submit button by default', () => {
      render(<SearchInput {...defaultProps} />);
      expect(screen.queryByText('Rechercher')).not.toBeInTheDocument();
    });

    it('should show submit button when showSubmitButton is true', () => {
      render(<SearchInput {...defaultProps} showSubmitButton />);
      expect(screen.getByText('Rechercher')).toBeInTheDocument();
    });

    it('should render custom submit text', () => {
      render(<SearchInput {...defaultProps} showSubmitButton submitText="Search" />);
      expect(screen.getByText('Search')).toBeInTheDocument();
    });

    it('should call onSubmit when form is submitted', () => {
      const onSubmit = vi.fn();
      render(<SearchInput {...defaultProps} showSubmitButton onSubmit={onSubmit} />);

      fireEvent.click(screen.getByText('Rechercher'));
      expect(onSubmit).toHaveBeenCalled();
    });

    it('should call onSubmit when Enter is pressed', () => {
      const onSubmit = vi.fn();
      render(<SearchInput {...defaultProps} onSubmit={onSubmit} />);

      const input = screen.getByPlaceholderText('Rechercher...');
      fireEvent.submit(input.closest('form')!);

      expect(onSubmit).toHaveBeenCalled();
    });
  });

  it('should be disabled when disabled prop is true', () => {
    render(<SearchInput {...defaultProps} disabled showSubmitButton />);

    const input = screen.getByPlaceholderText('Rechercher...');
    const submitButton = screen.getByText('Rechercher');

    expect(input).toBeDisabled();
    expect(submitButton).toBeDisabled();
  });

  it('should apply custom className', () => {
    const { container } = render(
      <SearchInput {...defaultProps} className="custom-class" />
    );

    expect(container.querySelector('form')).toHaveClass('custom-class');
  });
});

describe('InlineSearchInput', () => {
  const defaultProps = {
    value: '',
    onChange: vi.fn(),
  };

  it('should render inline search input', () => {
    render(<InlineSearchInput {...defaultProps} />);
    expect(screen.getByPlaceholderText('Rechercher...')).toBeInTheDocument();
  });

  it('should call onChange when typing', () => {
    const onChange = vi.fn();
    render(<InlineSearchInput {...defaultProps} onChange={onChange} />);

    const input = screen.getByPlaceholderText('Rechercher...');
    fireEvent.change(input, { target: { value: 'test' } });

    expect(onChange).toHaveBeenCalled();
  });

  it('should render custom placeholder', () => {
    render(<InlineSearchInput {...defaultProps} placeholder="Find..." />);
    expect(screen.getByPlaceholderText('Find...')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    const { container } = render(
      <InlineSearchInput {...defaultProps} className="custom-class" />
    );

    expect(container.firstChild).toHaveClass('custom-class');
  });
});
