import { render, screen, fireEvent } from '@testing-library/react';
import { ForceOverrideToggle } from '../ForceOverrideToggle';

describe('ForceOverrideToggle', () => {
  it('renders with protective state by default', () => {
    const mockToggle = jest.fn();
    render(<ForceOverrideToggle onToggle={mockToggle} />);
    
    expect(screen.getByText(/保护已手动修正的部门与位置信息/i)).toBeInTheDocument();
    expect(screen.queryByText(/确认执行强制覆盖？/i)).not.toBeInTheDocument();
  });

  it('shows confirmation modal when toggled on', () => {
    const mockToggle = jest.fn();
    render(<ForceOverrideToggle onToggle={mockToggle} />);
    
    const toggleButton = screen.getByRole('button');
    fireEvent.click(toggleButton);
    
    expect(screen.getByText(/确认执行强制覆盖？/i)).toBeInTheDocument();
    expect(mockToggle).not.toHaveBeenCalled(); // 此时不应触发回调
  });

  it('calls onToggle with true after confirmation', () => {
    const mockToggle = jest.fn();
    render(<ForceOverrideToggle onToggle={mockToggle} />);
    
    fireEvent.click(screen.getByRole('button'));
    fireEvent.click(screen.getByText(/我已知晓风险，继续/i));
    
    expect(mockToggle).toHaveBeenCalledWith(true);
    expect(screen.getByText(/系统将忽略现有数据，以 Excel 为准/i)).toBeInTheDocument();
  });
});
