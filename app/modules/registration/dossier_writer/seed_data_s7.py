"""S.7 稳定性模块 AI 填充配置种子数据

S.7 稳定性包含三个子章节：
- 3.2.S.7.1 稳定性总结和结论
- 3.2.S.7.2 批准后稳定性研究方案和承诺
- 3.2.S.7.3 稳定性数据

素材继承机制：
- 通用素材（如稳定性考察方案）可上传到 S.7 父章节
- 子章节可选择使用父章节素材
- 每个子章节也可有自己的专用素材
"""

# =============================================================================
# S.7.1 稳定性总结和结论
# =============================================================================

S7_1_ASSET_CATEGORIES = [
    {
        "chapter_code": "3.2.S.7.1",
        "category_name": "成品质量标准",
        "category_type": "document",
        "appendix_slot": None,
        "description": "成品（原料药）的质量标准文档，包含内包材、贮藏条件、有效期等信息",
        "sort_order": 1,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "category_name": "稳定性考察方案",
        "category_type": "document",
        "appendix_slot": None,
        "description": "稳定性研究方案文档，包含放置条件、考察时间、考察项目等试验设计信息",
        "sort_order": 2,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "category_name": "成品COA",
        "category_type": "document",
        "appendix_slot": None,
        "description": "成品检验报告单（Certificate of Analysis），包含批号、生产日期、包装材料等样品信息",
        "sort_order": 3,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "category_name": "稳定性考察结果表",
        "category_type": "document",
        "appendix_slot": None,
        "description": "稳定性考察数据汇总表，包含各时间点的检测结果，用于AI汇总趋势分析",
        "sort_order": 4,
    },
]


S7_1_FIELD_MAPPINGS = [
    # 表格1：样品信息（表3.2.S.7.1-1）
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "批号",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-1中'批号'行的第二列",
        "extraction_prompt": "从成品COA中提取稳定性考察样品的批号",
        "source_type": "asset_extract",
        "source_category": "成品COA",
        "sort_order": 1,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "生产日期",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-1中'生产日期'行的第二列",
        "extraction_prompt": "从成品COA中提取稳定性考察样品的生产日期",
        "source_type": "asset_extract",
        "source_category": "成品COA",
        "sort_order": 2,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "包装材料",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-1中'包装材料'行的第二列",
        "extraction_prompt": "从成品COA或成品质量标准中提取稳定性考察样品使用的包装材料信息",
        "source_type": "asset_extract",
        "source_category": "成品COA",
        "sort_order": 3,
        "is_required": True,
    },

    # 表格2：考察内容及结果（表3.2.S.7.1-2）— 影响因素
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "影响因素-高温-放置条件",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'影响因素-高温'行的'放置条件'列",
        "extraction_prompt": "从稳定性考察方案中提取影响因素试验高温条件的放置条件，如温度值",
        "source_type": "asset_extract",
        "source_category": "稳定性考察方案",
        "sort_order": 4,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "影响因素-高温-考察时间",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'影响因素-高温'行的'考察时间'列",
        "extraction_prompt": "从稳定性考察方案中提取影响因素试验高温条件的考察时间",
        "source_type": "asset_extract",
        "source_category": "稳定性考察方案",
        "sort_order": 5,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "影响因素-高温-考察项目",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'影响因素-高温'行的'考察项目'列",
        "extraction_prompt": "从稳定性考察方案中提取影响因素试验高温条件下需要检测的项目列表",
        "source_type": "asset_extract",
        "source_category": "稳定性考察方案",
        "sort_order": 6,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "影响因素-高湿-放置条件",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'影响因素-高湿'行的'放置条件'列",
        "extraction_prompt": "从稳定性考察方案中提取影响因素试验高湿条件的放置条件，如湿度值",
        "source_type": "asset_extract",
        "source_category": "稳定性考察方案",
        "sort_order": 7,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "影响因素-高湿-考察时间",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'影响因素-高湿'行的'考察时间'列",
        "extraction_prompt": "从稳定性考察方案中提取影响因素试验高湿条件的考察时间",
        "source_type": "asset_extract",
        "source_category": "稳定性考察方案",
        "sort_order": 8,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "影响因素-高湿-考察项目",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'影响因素-高湿'行的'考察项目'列",
        "extraction_prompt": "从稳定性考察方案中提取影响因素试验高湿条件下需要检测的项目列表",
        "source_type": "asset_extract",
        "source_category": "稳定性考察方案",
        "sort_order": 9,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "影响因素-光照-放置条件",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'影响因素-光照'行的'放置条件'列",
        "extraction_prompt": "从稳定性考察方案中提取影响因素试验光照条件的放置条件，如光照强度",
        "source_type": "asset_extract",
        "source_category": "稳定性考察方案",
        "sort_order": 10,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "影响因素-光照-考察时间",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'影响因素-光照'行的'考察时间'列",
        "extraction_prompt": "从稳定性考察方案中提取影响因素试验光照条件的考察时间",
        "source_type": "asset_extract",
        "source_category": "稳定性考察方案",
        "sort_order": 11,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "影响因素-光照-考察项目",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'影响因素-光照'行的'考察项目'列",
        "extraction_prompt": "从稳定性考察方案中提取影响因素试验光照条件下需要检测的项目列表",
        "source_type": "asset_extract",
        "source_category": "稳定性考察方案",
        "sort_order": 12,
        "is_required": True,
    },

    # 表格2：考察内容及结果 — 加速/中间/长期
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "加速试验-放置条件",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'加速试验'行的'放置条件'列",
        "extraction_prompt": "从稳定性考察方案中提取加速试验的放置条件，如温度40℃±2℃、湿度75%±5%",
        "source_type": "asset_extract",
        "source_category": "稳定性考察方案",
        "sort_order": 13,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "加速试验-考察时间",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'加速试验'行的'考察时间'列",
        "extraction_prompt": "从稳定性考察方案中提取加速试验的考察时间点，如0、1、2、3、6月",
        "source_type": "asset_extract",
        "source_category": "稳定性考察方案",
        "sort_order": 14,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "加速试验-考察项目",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'加速试验'行的'考察项目'列",
        "extraction_prompt": "从稳定性考察方案中提取加速试验条件下需要检测的项目列表",
        "source_type": "asset_extract",
        "source_category": "稳定性考察方案",
        "sort_order": 15,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "长期试验-放置条件",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'长期试验'行的'放置条件'列",
        "extraction_prompt": "从稳定性考察方案中提取长期试验的放置条件，如温度25℃±2℃、湿度60%±5%",
        "source_type": "asset_extract",
        "source_category": "稳定性考察方案",
        "sort_order": 16,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "长期试验-考察时间",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'长期试验'行的'考察时间'列",
        "extraction_prompt": "从稳定性考察方案中提取长期试验的考察时间点，如0、3、6、9、12、18、24、36月",
        "source_type": "asset_extract",
        "source_category": "稳定性考察方案",
        "sort_order": 17,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "长期试验-考察项目",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'长期试验'行的'考察项目'列",
        "extraction_prompt": "从稳定性考察方案中提取长期试验条件下需要检测的项目列表",
        "source_type": "asset_extract",
        "source_category": "稳定性考察方案",
        "sort_order": 18,
        "is_required": True,
    },

    # 表格2：AI 汇总结论
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "影响因素试验结论",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-2中'影响因素-结论'行，需要AI汇总",
        "extraction_prompt": "从稳定性考察结果表中汇总影响因素试验的数据趋势，总结各检测项目在试验条件下的变化情况，判断是否合格",
        "source_type": "asset_extract",
        "source_category": "稳定性考察结果表",
        "sort_order": 19,
        "is_required": True,
    },

    # 表格3：研究结论（表3.2.S.7.1-3）
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "内包材",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-3中'内包材'行的第二列",
        "extraction_prompt": "从成品质量标准中提取直接接触药品的内包材信息",
        "source_type": "asset_extract",
        "source_category": "成品质量标准",
        "sort_order": 20,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "贮藏条件",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-3中'贮藏条件'行的第二列",
        "extraction_prompt": "从成品质量标准中提取药品的贮藏条件要求",
        "source_type": "asset_extract",
        "source_category": "成品质量标准",
        "sort_order": 21,
        "is_required": True,
    },
    {
        "chapter_code": "3.2.S.7.1",
        "field_name": "有效期",
        "field_type": "text",
        "location_type": "table",
        "location_hint": "表3.2.S.7.1-3中'有效期'行的第二列",
        "extraction_prompt": "从成品质量标准中提取药品的有效期信息",
        "source_type": "asset_extract",
        "source_category": "成品质量标准",
        "sort_order": 22,
        "is_required": True,
    },
]


# =============================================================================
# S.7.2 批准后稳定性研究方案和承诺（待补充）
# =============================================================================

S7_2_ASSET_CATEGORIES = []

S7_2_FIELD_MAPPINGS = []


# =============================================================================
# S.7.3 稳定性数据（待补充）
# =============================================================================

S7_3_ASSET_CATEGORIES = []

S7_3_FIELD_MAPPINGS = []
