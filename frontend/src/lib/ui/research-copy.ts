/**
 * 研发模块（交付文档模板 / 知识库 / 研发报告）的用户可见文案。
 *
 * 为什么集中在这里：这三个页面原先大量使用研发内部叫法（母本、槽位、锚点、
 * 重识别、留档、兜底、降级…），第一次使用的人读不懂，同一个东西还经常有两种叫法。
 * 现在把「一个概念只有一种叫法 + 一句话解释」收敛成常量，组件引用常量而不是各写一遍，
 * 以后改词只改这一个文件。
 *
 * 约束：本文件只影响界面显示文字。JSON 字段名、枚举值、路由、数据库列名一律不动，
 * 因此不会影响接口契约与已有数据。
 */

export interface TermCopy {
  /** 界面上显示的正式叫法 */
  name: string
  /** 表格列头、Tag 等空间紧张处用的短叫法 */
  short: string
  /** 一句话解释：它是什么、为什么需要它 */
  hint: string
}

/**
 * 跨模块共用的术语表。
 * 使用方式：`TERMS.slot.name` 显示名字，`TERMS.slot.hint` 放进 Tooltip / extra 里解释。
 */
export const TERMS: Record<
  | 'templateFile'
  | 'slot'
  | 'candidate'
  | 'anchor'
  | 'templateStructure'
  | 'version'
  | 'fileCode'
  | 'kbDocument'
  | 'kbParsed'
  | 'kbParsing'
  | 'kbQueued'
  | 'kbFailed'
  | 'kbCancelled',
  TermCopy
> = {
  templateFile: {
    name: 'Word 模板文件',
    short: '模板文件',
    hint: '你上传的原始 Word 文档。AI 会在这份文件里按位置填写内容，原有排版、表格和字体都保持不变。',
  },
  slot: {
    name: '填充项',
    short: '填充项',
    hint: '文档里留给 AI 填内容的一个位置，例如「批次数」对应的那一格。生成报告时 AI 会逐项填写。',
  },
  candidate: {
    name: '可填位置',
    short: '可填位置',
    hint: '系统在模板文件里找到的、可以放内容的位置。把需要的位置挑出来，它就成为一个填充项。',
  },
  anchor: {
    name: '定位位置',
    short: '位置',
    hint: '这个填充项最终要写进模板文件的哪一处，生成时靠它把内容写到正确的位置。',
  },
  templateStructure: {
    name: '填充项设置',
    short: '填充项',
    hint: '文档里哪些位置需要 AI 填写、每个位置写什么。系统会自动分析，也可以人工调整。',
  },
  version: {
    name: '历史版本',
    short: '版本',
    hint: '每次上传或替换 Word 模板文件都会自动存一份，随时可以恢复，覆盖错了也能找回。',
  },
  fileCode: {
    name: '文件编号',
    short: '文件编号',
    hint: '这份报告在公司文档体系里的编号，例如 RD-2024-001。没编号可以留空。',
  },
  kbDocument: {
    name: '资料',
    short: '资料',
    hint: '上传到项目知识库的文件。上传后自动处理成可检索的文字，AI 写报告时会从这里找依据。',
  },
  kbParsed: { name: '已入库', short: '已入库', hint: '资料已处理完，AI 可以检索到里面的内容。' },
  kbParsing: { name: '入库中', short: '入库中', hint: '正在把资料转换成可检索的文字，通常几分钟内完成。' },
  kbQueued: { name: '排队中', short: '排队中', hint: '已提交，等待系统处理。前面的资料处理完就会开始。' },
  kbFailed: { name: '处理失败', short: '失败', hint: '资料没能处理成功，可以点「重新处理」再试一次，或换一份文件。' },
  kbCancelled: {
    name: '已取消',
    short: '已取消',
    hint: '这次处理被取消了，不算失败。需要的话可以点「重新处理」。',
  },
}

/** 三个模块顶部统一的「怎么做」三步引导 */
export interface GuideStep {
  title: string
  description: string
}

export const TEMPLATE_COPY = {
  title: '交付文档模板',
  subtitle: `管理各阶段报告的 ${TERMS.templateFile.name}：上传一份排好版的 Word，AI 就在它上面填内容，生成初版文档，不用从零写。`,
  guideTitle: '三步就能用起来',
  guideSteps: [
    {
      title: `上传 ${TERMS.templateFile.name}`,
      description: '把排好版的 Word 拖进上传区，文件名就是模板名称。',
    },
    {
      title: '系统自动分析可填位置',
      description: `上传后自动找出文档里该填内容的位置，变成一个个${TERMS.slot.name}，不需要手工标注。`,
    },
    {
      title: '按需调整填充项',
      description: `对结果不满意时，点「${TERMS.templateStructure.name}」改名、补说明，或「重新分析结构」。`,
    },
  ] satisfies GuideStep[],
  uploadTitle: `上传 ${TERMS.templateFile.name}`,
  emptyTitle: `还没有任何模板：先上传一份 ${TERMS.templateFile.name}`,
  emptyDescription: '上传后系统会自动分析可填位置，随后就能在研发报告页用它生成文档。',
  deleteTitle: '删除这个模板？',
  deleteDescription: `会同时删除它的${TERMS.version.name}、${TERMS.slot.name}设置和示例写法，已按它生成的报告文档不受影响但无法再用这个模板重新生成。删除后不可恢复。`,
  replaceTitle: `将要替换 ${TERMS.templateFile.name}`,
  replaceDescription: `原来的文件会自动存为${TERMS.version.name}，随时可以恢复，不会真的丢失。`,
} as const

export const KB_COPY = {
  title: '知识库',
  subtitle: '上传项目资料后自动处理成可检索的文字，AI 写报告时会从这里找依据，也方便人工随时查阅。',
  guideTitle: '三步就能用起来',
  guideSteps: [
    {
      title: '选择项目',
      description: '在顶部选择要管理的项目；不选则查看全部项目的知识库情况。',
    },
    {
      title: '创建知识库',
      description: '一个项目一个知识库，创建时可以留空名称，系统会按项目名自动生成。',
    },
    {
      title: '上传资料',
      description: '把 PDF、Word、Excel 等资料拖进来，系统会自动处理成可检索的文字。',
    },
  ] satisfies GuideStep[],
  uploadTitle: '上传资料',
  emptyTitle: '这个项目还没有上传任何资料',
  emptyDescription: '把项目相关文档拖到上方上传区即可，系统会自动处理并让 AI 可以检索。',
  deleteTitle: '删除这个知识库？',
  deleteDescription: '会同时删除库里全部资料和已处理的文字内容，AI 之后写这个项目的报告时不再参考这些资料。删除后不可恢复。',
  removeDocTitle: '把这份资料从知识库移除？',
  removeDocDescription: '移除后 AI 写报告时不再参考它；原始文件如果本地还有，可以重新上传。',
  notConfiguredTitle: '知识库服务还没有开通',
  notConfiguredDescription: '这项功能需要管理员在后台开通知识库服务后才能使用，请联系系统管理员。',
} as const

export const REPORT_COPY = {
  title: '研发报告',
  subtitle: '用模板加项目资料，让 AI 生成研发总结、阶段报告、年度报告等文档，生成后可以下载 Word 继续修改。',
  guideTitle: '三步就能用起来',
  guideSteps: [
    {
      title: '选择项目',
      description: '在顶部选择项目；不选则查看全部项目的报告总览。',
    },
    {
      title: `新建报告并选择 ${TERMS.templateFile.name}`,
      description: '填写标题、类型，挑一份模板文件，AI 就在这份文件里填内容。',
    },
    {
      title: '查看进度并下载',
      description: '生成是后台任务，进度在列表里实时更新，完成后可直接下载 Word。',
    },
  ] satisfies GuideStep[],
  emptyTitle: '这个项目还没有报告',
  emptyDescription: `点「新建报告」，挑一份 ${TERMS.templateFile.name}，AI 就能生成第一份文档。`,
  deleteTitle: '删除这份报告？',
  deleteDescription: '会同时删除它的生成记录、已填写的内容和下载文件。已下载到本地的 Word 不受影响。删除后不可恢复。',
  regenerateTitle: '重新生成这份报告？',
  regenerateDescription:
    '会新建一次生成任务并覆盖当前文档，之前人工修正过的填写内容不会自动带过去。需要保留的话先下载当前版本。',
} as const