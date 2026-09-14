import React from 'react';
import { Table, Tag, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';

interface HeaderDef {
  key: string;
  title: string;
  width?: number;
}

// 对应后端 ImportV4PreviewResponse.items 的结构
interface ImportPreviewItem extends Record<string, any> {
  row_index: number;
  validation_status?: 'pass' | 'duplicate' | 'error';
  error_message?: string;
  is_duplicate?: boolean;
}

interface ImportCockpitProps {
  data: ImportPreviewItem[];
  headers?: HeaderDef[];
}

// 默认 fallback：如果后端没传 headers，使用这个本地定义
const DEFAULT_HEADERS: HeaderDef[] = [
  { key: 'row_index', title: '行号', width: 60 },
  { key: 'asset_no', title: '资产编号' },
  { key: 'label_no', title: '标签号' },
  { key: 'name', title: '设备名称' },
  { key: 'category_description', title: '资产类别说明' },
  { key: 'equipment_class', title: '设备分类' },
  { key: 'manufacturer', title: '制造商' },
  { key: 'model', title: '型号' },
  { key: 'current_cost', title: '当前成本' },
  { key: 'book_value', title: '帐面净值' },
  { key: 'quantity', title: '数量' },
  { key: 'department_name', title: '部门' },
  { key: 'location_text', title: '位置' },
  { key: 'status', title: '状态' },
  { key: 'scrap_status', title: '报废状态' },
  { key: 'scrap_time', title: '报废时间' },
  { key: 'equipment_tag', title: '设备位号' },
  { key: 'responsible_person_name', title: '负责人' },
  { key: 'specification', title: '设备规格' },
  { key: 'supplier', title: '供应商' },
  { key: 'production_date', title: '出厂日期' },
  { key: 'commissioning_date', title: '启用日期' },
  { key: 'description', title: '描述' },
];

export const ImportCockpit: React.FC<ImportCockpitProps> = ({ data, headers }: ImportCockpitProps) => {
  // 使用后端传来的 headers，如果没有则使用默认值
  const activeHeaders = headers || DEFAULT_HEADERS;

  // 动态生成列定义
  const columns: ColumnsType<any> = [
    ...activeHeaders.map(field => ({
      title: field.title,
      dataIndex: field.key,
      key: field.key,
      width: field.width || 120,
      ellipsis: true,
      render: (text: any) => text !== null && text !== undefined ? String(text) : '-',
    })),
    {
      title: '错误详情',
      key: 'error_detail',
      width: 200,
      ellipsis: true,
      render: (_, record: any) => {
        // V4 格式
        if (record.error_message) {
          return <span style={{ color: '#e03131', fontSize: 12 }}>{record.error_message}</span>;
        }
        // V3 格式
        if (record.validation_errors && record.validation_errors.length > 0) {
          return (
            <span style={{ color: '#e03131', fontSize: 12 }}>
              {record.validation_errors.join('; ')}
            </span>
          );
        }
        return '-';
      },
    },
    {
      title: '验证',
      key: 'validation',
      width: 100,
      fixed: 'right',
      render: (_, record: any) => {
        // V4 格式：validation_status 字段
        if (record.validation_status === 'pass') return <Tag color="success">通过</Tag>;
        if (record.validation_status === 'duplicate') return <Tag color="warning">重复</Tag>;
        
        // V3 格式：validation_errors 数组
        if (record.validation_errors && Array.isArray(record.validation_errors)) {
          if (record.validation_errors.length === 0) {
            return <Tag color="success">通过</Tag>;
          }
          return (
            <Tooltip title={record.validation_errors.join(', ')}>
              <Tag color="error">异常</Tag>
            </Tooltip>
          );
        }
        
        // 兜底：显示异常并尝试展示 error_message
        return (
          <Tooltip title={record.error_message || '未知错误'}>
            <Tag color="error">异常</Tag>
          </Tooltip>
        );
      },
    },
  ];

  return (
    <div style={{ overflowX: 'auto' }}>
      <Table
        columns={columns}
        dataSource={data}
        rowKey="row_index"
        pagination={{
        // 必须用 defaultPageSize（非受控）。pageSize 是受控属性，每次重渲染都会
        // 覆盖用户选择的每页条数，导致切换后立即弹回默认值。
        defaultPageSize: 50,
        showSizeChanger: true,     // 保留切换功能，用户可根据需要调整
        pageSizeOptions: ['20', '30', '50', '100'],  // 移除 200，避免单页数据过多
        showTotal: (total) => `共 ${total} 条数据`,
        showQuickJumper: true,     // 保留快速跳转
      }}
        size="small"
        scroll={{ 
        x: 'max-content',
        y: 600  // 表格主体区域最大高度 600px，超出部分内部滚动，表头固定在顶部
      }}
      />
    </div>
  );
};
