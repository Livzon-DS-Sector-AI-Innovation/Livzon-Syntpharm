/**
 * AI 文档生成接口已下线，openapi 不再产出这些 schema。
 * 本文件从下线前的 types/generated/schema.ts 抽取保留，仅供报告页 UI 与 API 层类型引用；
 * 后端对应端点已删除，这些类型不再代表可用契约。
 */

export type DocGenBatchUploadResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
            data: DocGenBatchUploadResult;
}

export type DocGenBatchUploadResult = {
            /** Created */
            created?: {
                [key: string]: string | number;
            }[];
            /** Versioned */
            versioned?: {
                [key: string]: string | number;
            }[];
            /** Skipped */
            skipped?: string[];
}

export type DocGenConfirmRequest = {
            /**
             * Slots
             * @description 填充项 key → 人工修正后的文本
             */
            slots?: {
                [key: string]: string;
            };
            /**
             * Outline
             * @description 大纲调整（启用/禁用/换标题/排序）
             */
            outline?: DocGenSectionAdjust[];
}

export type DocGenConversationData = {
            conversation: DocGenConversationResponse;
            /** Messages */
            messages?: DocGenMessageResponse[];
}

export type DocGenConversationDataResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
            data?: DocGenConversationData | null;
}

export type DocGenConversationResponse = {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Job Id
             * Format: uuid
             */
            job_id: string;
            /** Status */
            status: string;
            /** Round Count */
            round_count: number;
            /** Max Rounds */
            max_rounds: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
}

export type DocGenEvidenceItem = {
            /**
             * File Id
             * @default
             */
            file_id: string;
            /**
             * File Name
             * @default
             */
            file_name: string;
            /**
             * Source Label
             * @default
             */
            source_label: string;
            /** Page */
            page?: number | null;
            /**
             * Quote
             * @default
             */
            quote: string;
}

export type DocGenExtractedInfoResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
            /** Data */
            data: {
                [key: string]: DocGenSlotValueResponse[];
            };
}

export type DocGenInputFileResponse = {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Original Filename */
            original_filename: string;
            /**
             * Role
             * @enum {string}
             */
            role: "material" | "literature" | "report_draft" | "supplement";
            /** Size Bytes */
            size_bytes: number;
            /**
             * Page Count
             * @default 0
             */
            page_count: number;
            /**
             * Char Count
             * @default 0
             */
            char_count: number;
            /** Parse Status */
            parse_status: string;
            /** Warnings */
            warnings?: string[] | null;
}

export type DocGenJobDataResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
            data: DocGenJobResponse;
}

export type DocGenJobDetail = {
            job: DocGenJobResponse;
            /** Files */
            files?: DocGenInputFileResponse[];
            /** Slots */
            slots?: DocGenSlotValueResponse[];
            /** Sections */
            sections?: DocGenSectionResponse[];
}

export type DocGenJobDetailResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
            data: DocGenJobDetail;
}

export type DocGenJobListResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
            /** Data */
            data?: DocGenJobResponse[];
}

export type DocGenJobResponse = {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Report Id */
            report_id?: string | null;
            /** Project Id */
            project_id?: string | null;
            /** Template Code */
            template_code: string;
            /** Template Version */
            template_version: string;
            /** Status */
            status: string;
            /** Step */
            step: string;
            /** Progress */
            progress: number;
            /**
             * Has Document
             * @default false
             */
            has_document: boolean;
            /**
             * Has Report
             * @default false
             */
            has_report: boolean;
            /** Error Code */
            error_code?: string | null;
            /** Error Message */
            error_message?: string | null;
            /** Stats */
            stats?: {
                [key: string]: unknown;
            } | null;
            /** Meta */
            meta?: {
                [key: string]: unknown;
            } | null;
            /** Parent Job Id */
            parent_job_id?: string | null;
            /** Supplement Text */
            supplement_text?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Finished At */
            finished_at?: string | null;
}

export type DocGenJobUpdateRequest = {
            /**
             * Doc Code
             * @description 受控编码
             */
            doc_code?: string | null;
            /**
             * Doc Version
             * @description 版本号
             */
            doc_version?: string | null;
            /**
             * Drug Name
             * @description 品种名称
             */
            drug_name?: string | null;
            /**
             * Supplement Text
             * @description 补充说明（重新生成时自动沿用）
             */
            supplement_text?: string | null;
            /**
             * Template Code
             * @description 模板ID（变更模板）
             */
            template_code?: string | null;
}

export type DocGenKbCoverage = {
            /**
             * Source
             * @default none
             */
            source: string;
            /**
             * Source Label
             * @default
             */
            source_label: string;
            /**
             * Kb Id
             * @default
             */
            kb_id: string;
            /**
             * Kb Name
             * @default
             */
            kb_name: string;
            /**
             * Documents
             * @default 0
             */
            documents: number;
            /**
             * Chunks
             * @default 0
             */
            chunks: number;
            /**
             * Facts
             * @default 0
             */
            facts: number;
            /**
             * Truncated
             * @default false
             */
            truncated: boolean;
            /** Warnings */
            warnings?: string[];
            /**
             * Total
             * @default 0
             */
            total: number;
            /**
             * Checked
             * @default 0
             */
            checked: number;
            /**
             * Fillable
             * @default 0
             */
            fillable: number;
            /**
             * Partial
             * @default 0
             */
            partial: number;
            /**
             * Missing
             * @default 0
             */
            missing: number;
            /**
             * Skipped
             * @default 0
             */
            skipped: number;
            /**
             * Fillable Ratio
             * @default 0
             */
            fillable_ratio: number;
            /**
             * Weighted Ratio
             * @default 0
             */
            weighted_ratio: number;
            /** Slots */
            slots?: DocGenKbCoverageSlot[];
}

export type DocGenKbCoverageResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
            data: DocGenKbCoverage;
}

export type DocGenKbCoverageSlot = {
            /** Key */
            key: string;
            /**
             * Label
             * @default
             */
            label: string;
            /**
             * Kind
             * @default field
             */
            kind: string;
            /**
             * Required
             * @default false
             */
            required: boolean;
            /**
             * Status
             * @default no_material
             */
            status: string;
            /**
             * Status Label
             * @default
             */
            status_label: string;
            /**
             * Matched Terms
             * @default 0
             */
            matched_terms: number;
}

export type DocGenLimits = {
            /**
             * Max Files
             * @default 20
             */
            max_files: number;
            /**
             * Max Total Pages
             * @default 150
             */
            max_total_pages: number;
            /**
             * Max File Mb
             * @default 30
             */
            max_file_mb: number;
            /**
             * Max Total Mb
             * @default 150
             */
            max_total_mb: number;
            /** Allowed Extensions */
            allowed_extensions?: string[];
            /** Supported Formats */
            supported_formats?: DocGenSupportedFormat[];
}

export type DocGenLimitsResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
            data: DocGenLimits;
}

export type DocGenMessageResponse = {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Role */
            role: string;
            /** Content */
            content: string;
            /** Slot Updates */
            slot_updates?: unknown[] | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
}

export type DocGenOperationResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
}

export type DocGenOutlineResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
            /** Data */
            data?: DocGenSectionResponse[];
}

export type DocGenSectionAdjust = {
            /** Section Key */
            section_key: string;
            /** State */
            state?: ("enabled" | "disabled") | null;
            /** Title */
            title?: string | null;
            /** Order Index */
            order_index?: number | null;
}

export type DocGenSectionResponse = {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Section Key */
            section_key: string;
            /** Fragment Key */
            fragment_key: string;
            /** Extension Point Key */
            extension_point_key: string;
            /** Parent Section Key */
            parent_section_key?: string | null;
            /** Level */
            level: number;
            /** Title */
            title: string;
            /** Order Index */
            order_index: number;
            /** Source */
            source: string;
            /** State */
            state: string;
            /** Trigger Trace */
            trigger_trace?: {
                [key: string]: unknown;
            } | null;
            /** Title Pool */
            title_pool?: string[];
}

export type DocGenSendMessageRequest = {
            /**
             * Content
             * @description 用户消息内容
             */
            content: string;
}

export type DocGenSendMessageResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
            data?: DocGenConversationData | null;
}

export type DocGenSlotValueResponse = {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Slot Key */
            slot_key: string;
            /** Label */
            label: string;
            /** Text */
            text?: string | null;
            /** Rows */
            rows?: unknown[] | null;
            /** State */
            state: string;
            /** Reason */
            reason?: string | null;
            /** Confidence */
            confidence?: number | null;
            /** Evidence */
            evidence?: DocGenEvidenceItem[] | null;
            /** Candidates */
            candidates?: unknown[] | null;
            /** Section Key */
            section_key?: string | null;
            /** Instance Index */
            instance_index?: number | null;
            /** Pre Compose Text */
            pre_compose_text?: string | null;
}

export type DocGenSupersededItem = {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Status */
            status: string;
            /** Step */
            step: string;
            /** Progress */
            progress: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Finished At */
            finished_at?: string | null;
}

export type DocGenSupersededList = {
            /** Items */
            items?: DocGenSupersededItem[];
            /**
             * Total
             * @default 0
             */
            total: number;
}

export type DocGenSupersededResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
            data: DocGenSupersededList;
}

export type DocGenSupportedFormat = {
            /** Name */
            name: string;
            /** Extensions */
            extensions?: string[];
            /** Library */
            library: string;
            /**
             * Needs Ocr
             * @default false
             */
            needs_ocr: boolean;
}

export type DocGenTemplateFileData = {
            /** Id */
            id: string;
            /** File Name */
            file_name?: string | null;
            /** File Ext */
            file_ext?: string | null;
}

export type DocGenTemplateFileResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
            data: DocGenTemplateFileData;
}

export type DocGenTemplateVersionItem = {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Version No */
            version_no: number;
            /** File Name */
            file_name?: string | null;
            /** File Ext */
            file_ext?: string | null;
            /** File Size */
            file_size?: number | null;
            /** Template Code */
            template_code?: string | null;
            /** Change Note */
            change_note?: string | null;
            /**
             * Is Current
             * @default false
             */
            is_current: boolean;
            /** Created By */
            created_by?: string | null;
            /** Created By Name */
            created_by_name?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
}

export type DocGenTemplateVersionListResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
            /** Data */
            data?: DocGenTemplateVersionItem[];
}

export type DocGenTemplateVersionRestoreData = {
            /** Id */
            id: string;
            /** Template Id */
            template_id: string;
            /** Version No */
            version_no: number;
            /** From Version No */
            from_version_no: number;
            /** File Name */
            file_name?: string | null;
            /** File Ext */
            file_ext?: string | null;
}

export type DocGenTemplateVersionRestoreResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
            data: DocGenTemplateVersionRestoreData;
}

export type DocGenUsableTemplate = {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Template Code */
            template_code: string;
            /** Template Version */
            template_version: string;
            /** Stage */
            stage: string;
            /**
             * Description
             * @default
             */
            description: string;
            /** File Name */
            file_name?: string | null;
            /** File Ext */
            file_ext?: string | null;
            /**
             * Slot Count
             * @default 0
             */
            slot_count: number;
            /**
             * Required Count
             * @default 0
             */
            required_count: number;
            /** Unfilled Notes */
            unfilled_notes?: string[];
}

export type DocGenUsableTemplateListResponse = {
            /**
             * Code
             * @default 200
             */
            code: number;
            /**
             * Message
             * @default success
             */
            message: string;
            /** Data */
            data?: DocGenUsableTemplate[];
}
