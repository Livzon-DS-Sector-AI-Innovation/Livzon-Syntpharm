import { useState } from 'react';
import { AlertOutlined, SafetyCertificateOutlined } from '@ant-design/icons';

interface ForceOverrideToggleProps {
  onToggle: (enabled: boolean) => void;
}

export const ForceOverrideToggle = ({ onToggle }: ForceOverrideToggleProps) => {
  const [isEnabled, setIsEnabled] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleToggle = () => {
    if (!isEnabled) {
      setShowConfirm(true);
    } else {
      setIsEnabled(false);
      onToggle(false);
    }
  };

  const confirmOverride = () => {
    setIsEnabled(true);
    onToggle(true);
    setShowConfirm(false);
  };

  return (
    <>
      <div className="flex items-center gap-4 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
        <div className="flex flex-col">
          <span className="text-sm font-medium text-slate-200 flex items-center gap-2">
            {isEnabled ? (
              <AlertOutlined className="text-amber-500" />
            ) : (
              <SafetyCertificateOutlined className="text-slate-400" />
            )}
            强制覆盖业务字段
          </span>
          <span className="text-xs text-slate-500 mt-1 font-mono">
            {isEnabled
              ? "⚠️ 系统将忽略现有数据，以 Excel 为准"
              : "✅ 保护已手动修正的部门与位置信息"}
          </span>
        </div>

        <button
          onClick={handleToggle}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 focus:ring-offset-slate-900 ${
            isEnabled ? 'bg-amber-500' : 'bg-slate-600'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${
              isEnabled ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {showConfirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 backdrop-blur-sm">
          <div className="bg-slate-900 border border-amber-500/50 p-6 rounded-lg max-w-md shadow-2xl">
            <h3 className="text-lg font-bold text-amber-500 mb-2 flex items-center gap-2">
              <AlertOutlined /> 确认执行强制覆盖？
            </h3>
            <p className="text-slate-300 text-sm mb-6 leading-relaxed">
              此操作将<strong>永久替换</strong>数据库中现有的部门、位置和设备位号。
            </p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowConfirm(false)} className="px-4 py-2 text-sm text-slate-400 hover:text-white">
                取消
              </button>
              <button onClick={confirmOverride} className="px-4 py-2 text-sm bg-amber-600 hover:bg-amber-500 text-white rounded-md font-medium">
                我已知晓风险，继续
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
