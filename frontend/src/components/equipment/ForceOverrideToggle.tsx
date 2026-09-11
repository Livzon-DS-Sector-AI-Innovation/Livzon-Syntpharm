import { useState } from 'react';
import { ShieldOutlined, WarningOutlined, CheckCircleOutlined } from '@ant-design/icons';

interface ForceOverrideToggleProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
}

export const ForceOverrideToggle = ({ enabled, onToggle }: ForceOverrideToggleProps) => {
  const [showConfirm, setShowConfirm] = useState(false);

  const handleToggle = () => {
    if (!enabled) {
      setShowConfirm(true);
    } else {
      onToggle(false);
    }
  };

  return (
    <>
      <div 
        className={`flex items-center gap-4 p-3 rounded-lg border transition-all duration-300 cursor-pointer select-none ${
          enabled 
            ? 'bg-amber-500/10 border-amber-500/50 shadow-[0_0_15px_rgba(245,158,11,0.2)]' 
            : 'bg-slate-800/50 border-slate-700 hover:border-slate-600'
        }`}
        onClick={handleToggle}
      >
        <div className="flex flex-col">
          <span className={`text-sm font-bold flex items-center gap-2 transition-colors ${
            enabled ? 'text-amber-500' : 'text-slate-200'
          }`}>
            {enabled ? <WarningOutlined /> : <ShieldOutlined />}
            {enabled ? '强制覆盖业务字段' : '保护模式'}
          </span>
          <span className={`text-xs mt-1 font-mono transition-colors ${
            enabled ? 'text-amber-400/80' : 'text-slate-500'
          }`}>
            {enabled 
              ? "⚠️ 系统将忽略现有数据，以 Excel 为准" 
              : "✅ 保护已手动修正的部门与位置信息"}
          </span>
        </div>

        <div className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 ml-auto ${
          enabled ? 'bg-amber-500' : 'bg-slate-600'
        }`}>
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${
              enabled ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </div>
      </div>

      {showConfirm && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-amber-500/30 p-8 rounded-xl max-w-md shadow-2xl relative overflow-hidden">
            {/* Decorative background element */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/5 rounded-full -mr-10 -mt-10 blur-2xl"></div>
            
            <h3 className="text-xl font-bold text-amber-500 mb-4 flex items-center gap-3">
              <WarningOutlined className="text-2xl" /> 
              高风险操作确认
            </h3>
            
            <div className="space-y-4 text-slate-300 text-sm leading-relaxed">
              <p>您即将开启<strong>强制覆盖模式</strong>。</p>
              <div className="bg-slate-800/80 p-3 rounded border border-slate-700 font-mono text-xs">
                <div className="flex items-center gap-2 text-red-400 mb-1">
                  <span className="w-2 h-2 rounded-full bg-red-500"></span>
                  部门 (Department)
                </div>
                <div className="flex items-center gap-2 text-red-400 mb-1">
                  <span className="w-2 h-2 rounded-full bg-red-500"></span>
                  位置 (Location)
                </div>
                <div className="flex items-center gap-2 text-red-400">
                  <span className="w-2 h-2 rounded-full bg-red-500"></span>
                  设备位号 (Tag No.)
                </div>
              </div>
              <p>上述字段将被 Excel 中的数据<strong>永久替换</strong>，即使数据库中已有值。</p>
            </div>

            <div className="flex justify-end gap-3 mt-8">
              <button 
                onClick={() => setShowConfirm(false)} 
                className="px-5 py-2 text-sm text-slate-400 hover:text-white transition-colors"
              >
                取消操作
              </button>
              <button 
                onClick={() => { onToggle(true); setShowConfirm(false); }} 
                className="px-5 py-2 text-sm bg-amber-600 hover:bg-amber-500 text-white rounded-md font-medium shadow-lg shadow-amber-900/20 transition-all active:scale-95"
              >
                我已知晓风险，继续
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
