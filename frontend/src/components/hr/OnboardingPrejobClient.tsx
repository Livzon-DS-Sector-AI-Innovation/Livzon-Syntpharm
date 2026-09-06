'use client'
import { createOnboardingTrainingRecord } from '@/actions/hr'
import { Input } from "antd"
const CELL = { border: "1px solid #000", padding: "4px" }
const VALUE = { border: "1px solid #000", padding: "4px" }
const LABEL = { border: "1px solid #000", padding: "4px", backgroundColor: "#f0f0f0" }

import { useState } from 'react'
import { App, Radio, Button, Card, Select, Space, } from 'antd'
import {
  PrinterOutlined,
  DownloadOutlined
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Employee, SopCatalogItem } from '@/types/hr'
import {
  fetchEmployees,
  fetchNewEmployees,
  fetchPrejobTrainingPlan,
  fetchOnboardingEvaluationByEmployeeId,
  fetchOnboardingRecords
} from '@/lib/api/client/hr'
import { apiGet } from '@/lib/api/client'

const DEPT_CONTENT_MAP: Record<string, string[]> = {
  '人事行政部': [
    '公司级公用文件(详见附件一)',
    '部门级公用文件(详见附件二)',
    '人事行政部人事行政专员岗位文件(详见附件三)',
    '人事行政专员岗位职责(QP.PM.053)',
    '生产安全知识',
    '岗前培训计划',
  ]
}

const _TD_LABEL = {
  border: '1px solid #1f2937',
  padding: '8px'
} as React.CSSProperties

const _TD_VALUE = {
  border: '1px solid #1f2937',
  padding: '8px'
} as React.CSSProperties

const _TH = {
  border: '1px solid #1f2937',
  padding: '8px'
} as React.CSSProperties

export default function OnboardingPrejobClient() {
  const { message } = App.useApp()
  const [sopSearch, setSopSearch] = useState('')
  const [sopDept, setSopDept] = useState('')
  const [sopCat, setSopCat] = useState('')
  const [selectedSops, setSelectedSops] = useState<SopCatalogItem[]>([])
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string | null>(null)
  const [downloadingWord, setDownloadingWord] = useState(false)
  const [downloadingExcel, setDownloadingExcel] = useState(false)
  const [downloadingEval, setDownloadingEval] = useState(false)
  const [factory, setFactory] = useState<'old' | 'new'>('old')

  const fetcher = factory === 'old' ? fetchEmployees : fetchNewEmployees

  const { data: employees = [] } = useQuery<Employee[]>({
    queryKey: ['hr-employees-list', { factory, page_size: 200 }],
    queryFn: async () => {
      const res = await fetcher({ page_size: 200 })
      return (res.data || []) as Employee[]
    },
  })

  const { data: sopDepts = [] } = useQuery<{value:string,label:string}[]>({
    queryKey: ['hr-sop-departments'],
    queryFn: async () => {
      const res = await apiGet<string[]>('/api/v1/hr/sop-catalog/departments')
      return res.map((d: string) => ({value:d,label:d}))
    },
  })

  const { data: sopCats = [] } = useQuery<{value:string,label:string}[]>({
    queryKey: ['hr-sop-categories'],
    queryFn: async () => {
      const res = await apiGet<string[]>('/api/v1/hr/sop-catalog/categories')
      return res.map((c: string) => ({value:c,label:c}))
    },
  })

  const { data: trainers = [] } = useQuery<{value:string,label:string}[]>({
    queryKey: ['hr-trainers-list'],
    queryFn: async () => {
      const res = await apiGet<{name: string; department: string}[]>('/api/v1/hr/trainers?page_size=200')
      return res.map((t: { name: string; department: string }) => ({value:t.name,label:`${t.name}(${t.department})`}))
    },
  })

  const { data: allSops = [] } = useQuery<SopCatalogItem[]>({
    queryKey: ['hr-sop-catalog', { sopDept, sopCat, sopSearch }],
    queryFn: async () => {
      const params = new URLSearchParams({ page_size: '200' })
      if (sopDept) params.set('department', sopDept)
      if (sopCat) params.set('category', sopCat)
      if (sopSearch) params.set('keyword', sopSearch)
      const res = await apiGet<SopCatalogItem[]>(`/api/v1/hr/sop-catalog?${params.toString()}`)
      return res || []
    },
  })

  const _handleSearch = async (keyword: string) => {
    if (!keyword || keyword.length < 1) return
    // Search is handled by the query key change
  }

  const selectedEmployee = employees.find((e: Employee) => e.id === selectedEmployeeId)

  const [sopMethods, setSopMethods] = useState<Record<string, string>>({})
  const [sopTrainers, setSopTrainers] = useState<Record<string, string>>({})

  const updateSopMethod = (sopId: string, method: string) => {
    setSopMethods(prev => ({ ...prev, [sopId]: method }))
  }

  const toggleSop = (sop: SopCatalogItem) => {
    setSelectedSops(prev => {
      const exists = prev.find(s => s.id === sop.id)
      if (exists) return prev.filter(s => s.id !== sop.id)
      return [...prev, sop]
    })
  }

  const handleExportWord = async () => {
    if (!selectedEmployee) return message.warning('请先选择员工')
    setDownloadingWord(true)
    try {
      await createOnboardingTrainingRecord(selectedEmployee.employee_number, {
        employee_id: selectedEmployee.id,
        employee_name: selectedEmployee.name,
        training_items: selectedSops.map((s, i) => ({
          index: i + 1,
          file_name: s.file_name,
          sop_number: s.sop_number || '',
          trainer: sopTrainers[s.id] || '',
          method: sopMethods[s.id] || '',
        })),
        format: 'word'
      })
      message.success('导出成功')
    } catch (err: unknown) {
      message.error('导出失败: ' + (err instanceof Error ? err.message : '未知错误'))
    } finally {
      setDownloadingWord(false)
    }
  }

  const handleExportExcel = async () => {
    if (!selectedEmployee) return message.warning('请先选择员工')
    setDownloadingExcel(true)
    try {
      await createOnboardingTrainingRecord(selectedEmployee.employee_number, {
        employee_id: selectedEmployee.id,
        employee_name: selectedEmployee.name,
        training_items: selectedSops.map((s, i) => ({
          index: i + 1,
          file_name: s.file_name,
          sop_number: s.sop_number || '',
          trainer: sopTrainers[s.id] || '',
          method: sopMethods[s.id] || '',
        })),
        format: 'excel'
      })
      message.success('导出成功')
    } catch (err: unknown) {
      message.error('导出失败: ' + (err instanceof Error ? err.message : '未知错误'))
    } finally {
      setDownloadingExcel(false)
    }
  }

  const handleExportEval = async () => {
    if (!selectedEmployee) return message.warning('请先选择员工')
    setDownloadingEval(true)
    try {
      await fetchOnboardingEvaluationByEmployeeId(selectedEmployee.id, selectedEmployee.name)
      message.success('导出成功')
    } catch (err: unknown) {
      message.error('导出失败: ' + (err instanceof Error ? err.message : '未知错误'))
    } finally {
      setDownloadingEval(false)
    }
  }

  const handlePrint = () => {
    if (!selectedEmployee) return message.warning('请先选择员工')
    window.print()
  }

  return (
    <div className="space-y-6">
      {/* 顶部选择器和厂区切换 */}
      <Card>
        <Space wrap size="middle" align="center">
          <Radio.Group value={factory} onChange={(e) => { setFactory(e.target.value); setSelectedEmployeeId(null) }} optionType="button">
            <Radio.Button value="old">旧厂</Radio.Button>
            <Radio.Button value="new">新厂</Radio.Button>
          </Radio.Group>
          <Select
            showSearch
            placeholder="选择员工"
            value={selectedEmployeeId || undefined}
            onChange={(value) => setSelectedEmployeeId(value)}
            options={employees.map((e) => ({
              value: e.id,
              label: `${e.employee_number} - ${e.name} (${e.department})`
            }))}
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
            style={{ minWidth: 320 }}
          />
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={handleExportWord}
            loading={downloadingWord}
            disabled={!selectedEmployee}
          >
            导出Word
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleExportExcel}
            loading={downloadingExcel}
            disabled={!selectedEmployee}
          >
            导出Excel
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleExportEval}
            loading={downloadingEval}
            disabled={!selectedEmployee}
          >
            导出考核表
          </Button>
          <Button
            icon={<PrinterOutlined />}
            onClick={handlePrint}
            disabled={!selectedEmployee}
          >
            打印
          </Button>
        </Space>
      </Card>

      {selectedEmployee && (
        <div id="print-area" className="print-area">
          {/* ===== Part I: SOP 目录选择 ===== */}
          <Card className="no-print-padding">
            <div className="mb-4 flex items-center justify-between">
              <div className="font-bold text-base">第一部分：SOP 目录选择 Part I: SOP catalog selection</div>
              <Space>
                <Select
                  size="small"
                  placeholder="部门"
                  value={sopDept || undefined}
                  onChange={(v) => setSopDept(v || '')}
                  options={sopDepts}
                  allowClear
                  style={{ width: 140 }}
                />
                <Select
                  size="small"
                  placeholder="分类"
                  value={sopCat || undefined}
                  onChange={(v) => setSopCat(v || '')}
                  options={sopCats}
                  allowClear
                  style={{ width: 140 }}
                />
                <Input
                  size="small"
                  placeholder="搜索文件"
                  value={sopSearch}
                  onChange={(e) => setSopSearch(e.target.value)}
                  style={{ width: 160 }}
                  allowClear
                />
                <Button size="small" onClick={() => {
                  setSelectedSops(prev => {
                    const visibleIds = new Set(allSops.slice(0, 200).map(s => s.id))
                    const newOnes = allSops.slice(0, 200).filter(s => !prev.find(p => p.id === s.id))
                    return [...prev, ...newOnes]
                  })
                }}>全选当前页</Button>
                <Button size="small" onClick={() => {
                  setSelectedSops(prev => {
                    const visibleIds = new Set(allSops.slice(0, 200).map(s => s.id))
                    return prev.filter(s => !visibleIds.has(s.id))
                  })
                }}>取消全选</Button>
              </Space>
            </div>

            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <colgroup>
                <col style={{ width: '4%' }} /><col style={{ width: '10%' }} /><col style={{ width: '10%' }} />
                <col style={{ width: '10%' }} /><col style={{ width: '10%' }} />
                <col style={{ width: '10%' }} /><col style={{ width: '10%' }} />
                <col style={{ width: '8%' }} /><col style={{ width: '8%' }} /><col style={{ width: '8%' }} />
                <col style={{ width: '10%' }} /><col style={{ width: '10%' }} /><col style={{ width: '10%' }} />
              </colgroup>
              <tbody>
                {/* 表头 */}
                <tr style={{ background: '#f5f5f5' }}>
                  <td style={_TH}>序号</td>
                  <td style={_TH} colSpan={2}>文件编号 SOP No.</td>
                  <td style={_TH} colSpan={4}>文件名称 File name</td>
                  <td style={_TH} colSpan={2}>版本 Version</td>
                  <td style={_TH}>培训方式 Method</td>
                  <td style={_TH} colSpan={3}>选择</td>
                </tr>
                {allSops.slice(0, 200).map((item, i) => {
                  const checked = selectedSops.find(s => s.id === item.id)
                  return (
                    <tr key={item.id}>
                      <td style={_TD_VALUE}>{i + 1}</td>
                      <td style={_TD_VALUE} colSpan={2}>{item.sop_number || ''}</td>
                      <td style={_TD_VALUE} colSpan={4}>{item.file_name || ''}</td>
                      <td style={_TD_VALUE} colSpan={2}>{(item.version as string) || ''}</td>
                      <td style={_TD_VALUE}>
                        <Select size="small" value={sopMethods[item.id] || undefined}
                          onChange={v => updateSopMethod(item.id, v)}
                          options={[{value:'面授',label:'面授'},{value:'自学',label:'自学'},{value:'自学+面授',label:'自学+面授'}]}
                          placeholder="选择" style={{ width: '100%' }} />
                      </td>
                      <td style={_TD_VALUE} colSpan={3}>
                        <input type="checkbox" checked={!!checked} onChange={() => toggleSop(item)} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </Card>

          {/* ===== Part II & IV: 培训计划 + 完成确认 (匹配模板) ===== */}
          <Card className="no-print-padding">
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <colgroup>
                <col style={{ width: '4%' }} /><col style={{ width: '10%' }} /><col style={{ width: '10%' }} />
                <col style={{ width: '10%' }} /><col style={{ width: '10%' }} />
                <col style={{ width: '10%' }} /><col style={{ width: '10%' }} />
                <col style={{ width: '8%' }} /><col style={{ width: '8%' }} /><col style={{ width: '8%' }} />
                <col style={{ width: '10%' }} /><col style={{ width: '10%' }} /><col style={{ width: '10%' }} />
              </colgroup>
              <tbody>
                {/* 标题行 */}
                <tr>
                  <td colSpan={10} style={{...CELL, textAlign: 'center', fontWeight: 700, background: '#e8e8e8'}}>
                    第二部分：培训计划/内容 Part II: Training plans/content
                  </td>
                  <td colSpan={3} style={{...CELL, textAlign: 'center', fontWeight: 700, background: '#e8e8e8'}}>
                    第四部分：培训完成情况确认 Part IV: Training completion
                  </td>
                </tr>
                {/* 表头 */}
                <tr style={{ background: '#f5f5f5' }}>
                  <td style={CELL}></td>
                  <td style={CELL} colSpan={4}>培训内容 Training items</td>
                  <td style={CELL} colSpan={2}>计划完成期限 Plan date</td>
                  <td style={CELL} colSpan={2}>培训师 Trainer</td>
                  <td style={CELL}>培训方式 Method</td>
                  <td style={CELL}>培训日期 Date</td>
                  <td style={CELL}>员工/日期</td>
                  <td style={CELL}>培训师/日期</td>
                </tr>
                {/* 培训明细行 */}
                {selectedSops.length > 0 ? selectedSops.map((item, i) => (
                  <tr key={i}>
                    <td style={{...CELL, textAlign: 'center'}}>{i + 1}</td>
                    <td style={CELL} colSpan={4}>{item.sop_number ? `${item.sop_number} ` : ''}{item.file_name || ''}</td>
                    <td style={CELL} colSpan={2}></td>
                    <td style={CELL} colSpan={2}>
                      <Select size="small" value={sopTrainers[item.id] || undefined}
                        onChange={v => setSopTrainers(prev => ({...prev, [item.id]: v}))}
                        options={trainers} placeholder="选培训师" style={{ width: '100%' }}
                        showSearch filterOption={(input, option) => (option?.label||'').toLowerCase().includes(input.toLowerCase())} />
                    </td>
                    <td style={CELL}>
                      <Select size="small" value={sopMethods[item.id] || undefined}
                        onChange={v => updateSopMethod(item.id, v)}
                        options={[{value:'面授',label:'面授'},{value:'自学',label:'自学'},{value:'自学+面授',label:'自学+面授'}]}
                        placeholder="选择" style={{ width: '100%' }} />
                    </td>
                    <td style={CELL}></td><td style={CELL}></td><td style={CELL}></td>
                  </tr>
                )) : (
                  <tr><td style={CELL} colSpan={13}>请在上方 SOP 目录中勾选培训内容</td></tr>
                )}
                {/* Part III: 审核批准 */}
                <tr>
                  <td colSpan={10} style={{...CELL, textAlign: 'center', fontWeight: 700, background: '#e8e8e8'}}>
                    第三部分：培训计划审核批准 Part III: Training plans review and approval
                  </td>
                  <td colSpan={3} style={{...CELL, textAlign: 'center', fontWeight: 700, background: '#e8e8e8'}}>
                    备注 Remarks
                  </td>
                </tr>
                <tr>
                  <td style={LABEL} colSpan={3}>部门/日期<br/>Dept./Date</td>
                  <td style={VALUE} colSpan={2}></td>
                  <td style={LABEL} colSpan={2}>HR/日期<br/>HR/Date</td>
                  <td style={VALUE} colSpan={3}></td>
                  <td style={LABEL}>QA/日期<br/>QA/Date</td>
                  <td style={VALUE} colSpan={2}></td>
                  <td style={VALUE} colSpan={3}></td>
                </tr>
              </tbody>
            </table>
          </Card>
        </div>
      )}
      <style>{`
        @media print {
          .no-print { display: none !important; }
          .no-print-padding .ant-card-body { padding: 0 !important; }
        }
      `}</style>
    </div>
  )
}
