import type { DeviationAiAnalysisData, DeviationInvestigationPrefill } from '@/types/quality'

/** 行首编号 / 项目符号：`1.` `1、` `(1)` `（1）` `1)` `-` `•` `·` `*` */
const NUMBERING_PREFIX = /^\s*(?:[(（]\s*\d{1,2}\s*[)）]|\d{1,2}\s*[.、)）]|[-•·*])\s*/

/**
 * 把 AI 的「CAPA 建议」拆成多条 CAPA 行内容。
 *
 * 规则：按换行切分 → 去掉行首编号/项目符号 → 去空白 → 过滤空串。
 * 若整段没有换行（AI 常常一段话给多条），退化为按中文分号 / 句号切分，避免全部塞进一条。
 */
export function splitCapaSuggestion(text: string): string[] {
  const cleaned = (value: string): string => value.replace(NUMBERING_PREFIX, '').trim()
  const lines = text
    .split(/\r?\n/)
    .map(cleaned)
    .filter((line) => line.length > 0)
  if (lines.length > 1) return lines
  const single = cleaned(text)
  if (!single) return []
  const sentences = single
    .split(/[；;。]/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
  return sentences.length > 1 ? sentences : [single]
}

/**
 * 由 AI 分析结果构造调查表单填充载荷；四项全空时返回 null。
 * 只做字段映射，不做覆盖判断（覆盖策略在调查表单内实现：只补空白）。
 */
export function buildInvestigationPrefill(
  analysis: Pick<DeviationAiAnalysisData, 'description' | 'reason' | 'risk_assessment' | 'capa_suggestion'>,
): DeviationInvestigationPrefill | null {
  const description = (analysis.description ?? '').trim()
  const reason = (analysis.reason ?? '').trim()
  const risk = (analysis.risk_assessment ?? '').trim()
  const capa = splitCapaSuggestion(analysis.capa_suggestion ?? '')
  if (!description && !reason && !risk && capa.length === 0) return null
  return {
    //: 每次点击生成新 nonce：即使内容相同也要重新尝试填充一次
    nonce: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    nonconformity_description: description,
    root_cause_analysis: reason,
    risk_assessment: risk,
    capa_proposals: capa.map((summary) => ({ summary })),
  }
}