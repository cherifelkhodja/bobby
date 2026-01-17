import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Input } from './Input';

describe('Input', () => {
  it('should render input element', () => {
    render(<Input />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('should render label when provided', () => {
    render(<Input label="Email" />);
    expect(screen.getByText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
  });

  it('should generate id from label', () => {
    render(<Input label="Email Address" />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('id', 'email-address');
  });

  it('should use custom id when provided', () => {
    render(<Input label="Email" id="custom-id" />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('id', 'custom-id');
  });

  it('should display error message', () => {
    render(<Input error="Ce champ est requis" />);
    expect(screen.getByText('Ce champ est requis')).toBeInTheDocument();
  });

  it('should display helper text', () => {
    render(<Input helperText="Enter your email" />);
    expect(screen.getByText('Enter your email')).toBeInTheDocument();
  });

  it('should not display helper text when error is present', () => {
    render(<Input error="Error message" helperText="Helper text" />);
    expect(screen.getByText('Error message')).toBeInTheDocument();
    expect(screen.queryByText('Helper text')).not.toBeInTheDocument();
  });

  it('should apply error styling when error is present', () => {
    render(<Input error="Error" />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveClass('input-error');
  });

  it('should forward ref to input element', () => {
    const ref = vi.fn();
    render(<Input ref={ref} />);
    expect(ref).toHaveBeenCalled();
  });

  it('should handle value change', () => {
    const onChange = vi.fn();
    render(<Input onChange={onChange} />);

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'test' } });

    expect(onChange).toHaveBeenCalled();
  });

  it('should accept input props', () => {
    render(
      <Input
        type="email"
        placeholder="Enter email"
        disabled
        required
      />
    );

    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('type', 'email');
    expect(input).toHaveAttribute('placeholder', 'Enter email');
    expect(input).toBeDisabled();
    expect(input).toBeRequired();
  });

  it('should apply custom className', () => {
    render(<Input className="custom-class" />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveClass('custom-class');
  });
});
