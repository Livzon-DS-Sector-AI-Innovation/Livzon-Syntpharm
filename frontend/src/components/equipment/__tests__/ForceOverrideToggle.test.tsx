import { render, screen, fireEvent } from '@testing-library/react';
import { ForceOverrideToggle } from '../ForceOverrideToggle';

describe('ForceOverrideToggle (Industrial Safety Design)', () => {
  it('renders in protective mode by default', () => {
    const mockToggle = jest.fn();
    render(<ForceOverrideToggle enabled={false} onToggle={mockToggle} />);
    
    expect(screen.getByText(/保护模式/i)).toBeTruthy();
    expect(screen.getByText(/保护已手动修正的部门与位置信息/i)).toBeTruthy();
  });

  it('shows custom industrial-style confirmation modal when toggled on', () => {
    const mockToggle = jest.fn();
    render(<ForceOverrideToggle enabled={false} onToggle={mockToggle} />);
    
    const container = screen.getByText(/保护模式/i).closest('div');
    if (container) fireEvent.click(container);
    
    expect(screen.getByText(/高风险操作确认/i)).toBeTruthy();
    expect(screen.getByText(/部门 \(Department\)/i)).toBeTruthy();
  });

  it('calls onToggle with true after user confirms the risk', () => {
    const mockToggle = jest.fn();
    render(<ForceOverrideToggle enabled={false} onToggle={mockToggle} />);
    
    // Open modal
    const container = screen.getByText(/保护模式/i).closest('div');
    if (container) fireEvent.click(container);
    
    // Confirm
    fireEvent.click(screen.getByText(/我已知晓风险，继续/i));
    
    expect(mockToggle).toHaveBeenCalledWith(true);
  });

  it('switches to warning state with amber glow when enabled', () => {
    const mockToggle = jest.fn();
    render(<ForceOverrideToggle enabled={true} onToggle={mockToggle} />);
    
    expect(screen.getByText(/强制覆盖业务字段/i)).toBeTruthy();
    expect(screen.getByText(/系统将忽略现有数据，以 Excel 为准/i)).toBeTruthy();
  });
});
