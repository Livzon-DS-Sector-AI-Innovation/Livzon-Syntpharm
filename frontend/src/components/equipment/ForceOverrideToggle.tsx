import { Switch, Popconfirm } from 'antd';
import { SafetyOutlined, WarningOutlined } from '@ant-design/icons';

interface ForceOverrideToggleProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
}

export const ForceOverrideToggle = ({ enabled, onToggle }: ForceOverrideToggleProps) => {
  return (
    <Popconfirm
      title={enabled ? '关闭强制覆盖' : '开启强制覆盖'}
      description={
        enabled ? (
          <div style={{ maxWidth: 280, fontSize: 13, lineHeight: 1.6, color: '#5d5b54' }}>
            <p style={{ margin: 0 }}>
              关闭后将恢复<strong>保护模式</strong>，仅当数据库字段为空时才写入 Excel 值。
            </p>
          </div>
        ) : (
          <div style={{ maxWidth: 280, fontSize: 13, lineHeight: 1.6, color: '#5d5b54' }}>
            <p style={{ margin: '0 0 8px' }}>
              <strong style={{ color: '#f59e0b' }}>强制覆盖</strong>：强制覆盖模式下，按资产编号匹配已有记录。
            </p>
            <p style={{ margin: '0 0 8px' }}>
              无条件覆盖所有业务字段：
            </p>
            <ul style={{ margin: 0, paddingLeft: 18, color: '#ef4444', fontWeight: 500, fontSize: 12 }}>
              <li>标签号、设备位号、设备分类、设备名称</li>
              <li>负责人、状态、资产类别说明、型号、规格</li>
              <li>制造商、供应商、报废状态、报废时间</li>
              <li>投产日期、投用日期、描述、部门、位置</li>
            </ul>
          </div>
        )
      }
      onConfirm={() => onToggle(!enabled)}
      okText={enabled ? '确认关闭' : '确认开启'}
      cancelText="取消"
      okButtonProps={{ danger: enabled, size: 'small' }}
      cancelButtonProps={{ size: 'small' }}
      icon={enabled ? <SafetyOutlined style={{ color: '#10b981' }} /> : <WarningOutlined style={{ color: '#f59e0b' }} />}
    >
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          padding: '4px 12px',
          borderRadius: 6,
          border: `1px solid ${enabled ? '#fde68a' : '#e5e3df'}`,
          background: enabled ? '#fffbeb' : '#ffffff',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          userSelect: 'none',
        }}
      >
        <span style={{
          fontSize: 13,
          fontWeight: 500,
          color: enabled ? '#f59e0b' : '#78716C',
          display: 'flex',
          alignItems: 'center',
          gap: 4,
        }}>
          {enabled ? <WarningOutlined /> : <SafetyOutlined />}
          {enabled ? '强制覆盖' : '保护模式'}
        </span>
        <Switch
          size="small"
          checked={enabled}
          checkedChildren="覆盖"
          unCheckedChildren="保护"
          style={{
            background: enabled ? '#f59e0b' : undefined,
          }}
        />
      </div>
    </Popconfirm>
  );
};
