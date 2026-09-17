#!/usr/bin/env python3
"""
OCR Worker Process - 独立子进程运行 PaddleOCR

通过 stdin/stdout JSON 通信，隔离 PaddleOCR 的段错误风险。
如果此进程崩溃，主进程可以重启它而不影响后端服务。

通信协议：
- 主进程 → Worker: JSON 请求（每行一个）
- Worker → 主进程: JSON 响应（每行一个）
"""

import json
import sys
import traceback
from pathlib import Path


def process_request(request: dict, pp_ocr, get_pp_structure) -> dict:
    """处理单个 OCR 请求"""
    request_id = request.get("id")
    input_path = request.get("input_path")
    engine = request.get("engine", "pp_ocr")
    method = request.get("method", "extract_text")

    try:
        if engine == "pp_ocr":
            if method == "extract_text":
                result = pp_ocr.predict(input_path)
                texts = []
                for res in result:
                    if hasattr(res, "res") and "rec_texts" in res.res:
                        texts.extend(res.res["rec_texts"])
                return {"id": request_id, "status": "ok", "data": "\n".join(texts)}

            elif method == "extract_with_positions":
                result = pp_ocr.predict(input_path)
                blocks = []
                for res in result:
                    if hasattr(res, "res"):
                        rec_data = res.res
                        if all(k in rec_data for k in ["rec_texts", "rec_scores", "rec_polys"]):
                            for text, score, poly in zip(
                                rec_data["rec_texts"], rec_data["rec_scores"], rec_data["rec_polys"]
                            ):
                                x_coords = [p[0] for p in poly]
                                y_coords = [p[1] for p in poly]
                                blocks.append({
                                    "text": text,
                                    "bbox": [
                                        int(min(x_coords)),
                                        int(min(y_coords)),
                                        int(max(x_coords)),
                                        int(max(y_coords)),
                                    ],
                                    "confidence": float(score),
                                })
                return {"id": request_id, "status": "ok", "data": blocks}

        elif engine == "pp_structure":
            pp_structure = get_pp_structure()
            result = pp_structure.predict(input_path)

            if method == "extract_markdown":
                import tempfile

                markdown_parts = []
                for res in result:
                    if hasattr(res, "save_to_markdown"):
                        with tempfile.TemporaryDirectory() as tmpdir:
                            res.save_to_markdown(save_path=tmpdir)
                            md_files = list(Path(tmpdir).glob("*.md"))
                            if md_files:
                                markdown_parts.append(md_files[0].read_text(encoding="utf-8"))
                return {"id": request_id, "status": "ok", "data": "\n\n".join(markdown_parts)}

            elif method == "extract_structure":
                import tempfile

                output = {"markdown": "", "json": {}, "layout": [], "tables": []}
                for res in result:
                    if hasattr(res, "save_to_markdown"):
                        with tempfile.TemporaryDirectory() as tmpdir:
                            res.save_to_markdown(save_path=tmpdir)
                            md_files = list(Path(tmpdir).glob("*.md"))
                            if md_files:
                                output["markdown"] = md_files[0].read_text(encoding="utf-8")

                    if hasattr(res, "save_to_json"):
                        with tempfile.TemporaryDirectory() as tmpdir:
                            res.save_to_json(save_path=tmpdir)
                            json_files = list(Path(tmpdir).glob("*.json"))
                            if json_files:
                                with open(json_files[0], encoding="utf-8") as f:
                                    output["json"] = json.load(f)

                    if hasattr(res, "res"):
                        res_data = res.res
                        if "layout_parsing_res" in res_data:
                            for item in res_data["layout_parsing_res"]:
                                if "block_label" in item:
                                    if item["block_label"] == "table":
                                        output["tables"].append(item)
                                    output["layout"].append(item)
                return {"id": request_id, "status": "ok", "data": output}

        return {"id": request_id, "status": "error", "message": f"Unknown method: {method}"}

    except Exception as e:
        return {
            "id": request_id,
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc(),
        }


def main():
    """主循环：加载模型，处理请求"""
    # 将 PaddleOCR/Paddle 的日志重定向到 stderr，保持 stdout 干净
    import logging
    logging.getLogger("paddle").setLevel(logging.WARNING)
    logging.getLogger("paddleocr").setLevel(logging.WARNING)
    logging.getLogger("ppocr").setLevel(logging.WARNING)

    # 重定向 stdout 为 stderr（PaddleOCR 内部 print 到 stdout 的内容）
    # 我们自己的 JSON 通信使用 fd 1 的原始副本
    import os
    _json_out = os.fdopen(os.dup(1), "w", buffering=1)  # 复制 stdout fd

    def _emit(msg: dict) -> None:
        _json_out.write(json.dumps(msg, ensure_ascii=False) + "\n")
        _json_out.flush()

    _emit({"status": "initializing", "message": "Loading PaddleOCR models..."})

    # 将 stdout 重定向到 stderr，避免 PaddleOCR 的 print 污染 JSON 通道
    sys.stdout = sys.stderr

    try:
        from paddleocr import PaddleOCR

        # 初始化 PP-OCR（轻量级，快速加载）
        pp_ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        _emit({"status": "ready", "message": "PP-OCR ready, PP-StructureV3 will be loaded on first use"})

    except Exception as e:
        _emit({"status": "error", "message": f"Failed to initialize PP-OCR: {e}"})
        sys.exit(1)

    # PP-StructureV3 懒加载
    pp_structure = None

    def get_pp_structure():
        nonlocal pp_structure
        if pp_structure is None:
            _emit({"status": "initializing", "message": "Loading PP-StructureV3 on first use..."})
            from paddleocr import PPStructureV3
            pp_structure = PPStructureV3(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
            _emit({"status": "ready", "message": "PP-StructureV3 loaded"})
        return pp_structure

    # 处理请求
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            response = process_request(request, pp_ocr, get_pp_structure)
        except json.JSONDecodeError as e:
            response = {"status": "error", "message": f"Invalid JSON: {e}"}
        except Exception as e:
            response = {
                "status": "error",
                "message": str(e),
                "traceback": traceback.format_exc(),
            }

        _emit(response)


if __name__ == "__main__":
    main()
