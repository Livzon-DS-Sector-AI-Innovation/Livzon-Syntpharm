"""Scan for index-based location hints in FieldMapping and output JSON."""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.modules.registration.dossier_writer.field_models import FieldMapping


async def main():
    async with AsyncSessionLocal() as db:
        stmt = select(FieldMapping).where(~FieldMapping.is_deleted)
        result = await db.execute(stmt)
        mappings = result.scalars().all()

        findings = []
        for m in mappings:
            # Identify index-based anchors (e.g., "第3段")
            is_index_based = False
            if m.location_hint and m.location_hint.startswith("第") and m.location_hint.endswith("段"):
                try:
                    int(m.location_hint[1:-1])
                    is_index_based = True
                except ValueError:
                    pass

            if is_index_based:
                findings.append(
                    {
                        "mapping_id": str(m.id),
                        "chapter_code": m.chapter_code,
                        "field_name": m.field_name,
                        "location_type": m.location_type,
                        "old_hint": m.location_hint,
                        "candidate_text_anchor": None,  # To be filled by manual review or advanced logic
                    }
                )

        output = json.dumps(findings, indent=2, ensure_ascii=False)
        print(output)

        # Save to file for archiving
        output_path = "/tmp/location_hints_scan.json"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\n📁 Results archived to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
