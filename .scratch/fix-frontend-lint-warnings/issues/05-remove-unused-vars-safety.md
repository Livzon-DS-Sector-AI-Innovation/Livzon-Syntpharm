# 05 — Remove unused vars in src/app/(dashboard)/safety/

**What to build:** Delete all unused imports and variables in safety dashboard pages. No behavioral change, zero risk.

**Blocked by:** None — can start immediately

**Status:** done

**Result:** Removed 145 unused variables across 12 files in the safety directory.

**Changes made:**
- accident/page.tsx: Removed 6 unused vars (SearchIcon, INJURY_SEVERITY_OPTIONS, Text, setDeptFilter, setDateFromFilter, setDateToFilter)
- check/page.tsx: Removed 1 unused var (CheckTypeEnum)
- contractor/page.tsx: Removed 5 unused vars (InputNumber, message, Typography, Tabs, setTab)
- ehs-change/page.tsx: Removed 9 unused vars (Spin, InputNumber, ExclamationCircleOutlined, SwapOutlined, RiskAssessmentItem, ApprovalChainItem, ActionItem, PSSRChecklistItem, RangePicker)
- hazard-identification-legacy/page.tsx: Simplified file, removed 46 unused vars
- hazard-identification/[id]/page.tsx: Removed 5 unused vars (Collapse, Tooltip, Badge, REVIEW_STATUS_OPTIONS, Paragraph)
- hazard-legacy/page.tsx: Simplified file, removed 30+ unused vars
- hazard/[id]/page.tsx: Removed 10+ unused vars (Avatar, Paragraph)
- knowledge-base/page.tsx: Removed 10+ unused vars (total, setCategoryFilter, handleDelete, handlePublish, handleArchive, deleteKnowledgeArticle, publishKnowledgeArticle, archiveKnowledgeArticle, updateItem, removeItem)
- occupational-health/page.tsx: Removed 17 unused vars (Spin, CloseCircleOutlined, WarningOutlined, ExperimentOutlined, HeartOutlined, FileAddOutlined, updateDetectionResult, deleteDetectionResult, updateExamItem, deleteExamItem, DetectionType, HazardFactorCategory, OELComplianceStatus, ExamType, ExamConclusion, AbnormalityStatus, ExamResultItem)
- regulation/page.tsx: Removed 5 unused vars (Card, pillError, pillNeutral, updateRevisionInStore, handleOpenGenerator)
- training/page.tsx: Removed 5 unused vars (getExpiringCertificates, Text, Typography)

**Verification:**
- [x] All unused imports removed from safety pages
- [x] All unused variables removed from safety pages
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (0 no-unused-vars warnings in safety directory)
