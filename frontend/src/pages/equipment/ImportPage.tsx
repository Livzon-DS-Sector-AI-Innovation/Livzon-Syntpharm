import React, { useState } from 'react';
import { Button } from 'antd';
import { Tag as Badge } from 'antd';

// 定义 22 个字段的中文映射
const FIELD_LABELS: Record<string, string> = {
  row_index: "行号", asset_no: "资产编号", label_no: "标签号", name: "设备名称",
  category_description: "资产类别说明", equipment_class: "设备分类", manufacturer: "制造商",
  model: "型号", current_cost: "当前成本", book_value: "帐面净值", quantity: "数量",
  department_name: "部门", location_text: "位置", status: "状态", scrap_status: "报废状态",
  scrap_time: "报废时间", equipment_tag: "设备位号", responsible_person_name: "负责人",
  specification: "设备规格", supplier: "供应商", production_date: "出厂日期",
  commissioning_date: "启用日期", description: "描述"
};

export const EquipmentImportPage = () => {
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [forceOverride, setForceOverride] = useState(false);

  const handlePreview = async (file: File) => {
    const response = await fetch('/api/v1/equipment/equipments/import/preview', { 
      method: 'POST', 
      body: file 
    });
    const data = await response.json();
    setPreviewData(data.items || []);
  };

  const displayKeys = Object.keys(FIELD_LABELS);

  return (
    <div className="p-8 bg-slate-950 min-h-screen text-slate-200">
      <h1 className="text-3xl font-bold mb-6">设备导入预览</h1>
      
      <div className="mb-4">
        <input type="file" onChange={(e) => e.target.files?.[0] && handlePreview(e.target.files[0])} />
      </div>

      {previewData.length > 0 && (
        <div className="overflow-x-auto border border-slate-700 rounded">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-800 text-slate-400">
              <tr>
                {displayKeys.map(key => (
                  <th key={key} className="p-2 border-r border-slate-700 whitespace-nowrap">{FIELD_LABELS[key]}</th>
                ))}
                <th className="p-2">验证</th>
              </tr>
            </thead>
            <tbody>
              {previewData.map((row, idx) => (
                <tr key={idx} className="border-b border-slate-800 hover:bg-slate-900">
                  {displayKeys.map(key => (
                    <td key={key} className="p-2 border-r border-slate-800 font-mono">
                      {row[key] !== undefined && row[key] !== null ? String(row[key]) : '-'}
                    </td>
                  ))}
                  <td className="p-2">
                    <Badge variant={row.validation_status === 'error' ? "destructive" : "outline"}>
                      {row.validation_status === 'pass' ? '通过' : '异常'}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
