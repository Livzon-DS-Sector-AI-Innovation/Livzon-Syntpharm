import React from 'react';
import { CheckCircle, AlertCircle, FileText } from 'lucide-react';

interface BatchStats {
  batch_id: string;
  created_count: number;
  updated_count: number;
  skipped_count: number;
  error_count: number;
}

export const BatchTracker: React.FC<{ stats: BatchStats }> = ({ stats }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6 mt-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
          <FileText className="h-5 w-5 text-sky-400" />
          同步完成报告
        </h3>
        <code className="text-xs bg-slate-800 px-2 py-1 rounded text-sky-300">
          Batch ID: {stats.batch_id}
        </code>
      </div>
      
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="新建设备" value={stats.created_count} color="text-emerald-400" />
        <StatCard label="更新价值" value={stats.updated_count} color="text-sky-400" />
        <StatCard label="跳过记录" value={stats.skipped_count} color="text-slate-400" />
        <StatCard label="错误信息" value={stats.error_count} color="text-red-400" />
      </div>
    </div>
  );
};

const StatCard = ({ label, value, color }: any) => (
  <div className="bg-slate-800/50 p-4 rounded border border-slate-700/50">
    <div className={`text-2xl font-mono font-bold ${color}`}>{value}</div>
    <div className="text-xs text-slate-500 uppercase tracking-wider">{label}</div>
  </div>
);
