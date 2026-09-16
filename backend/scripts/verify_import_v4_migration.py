"""验证设备导入 v4 迁移是否完成。"""
import asyncio
import sys
import os
sys.path.insert(0, '/home/zhuangweizi/Livzon-Syntpharm/backend')

# 强制使用 Docker 内部主机名
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:postgres123@erp-postgres:5432/dazah'

from app.core.database import async_session_factory
from sqlalchemy import text

async def verify():
    async with async_session_factory() as db:
        print("🔍 开始验证设备导入 v4 迁移...")

        # 1. 检查 is_fixed_asset 字段
        try:
            await db.execute(text("SELECT is_fixed_asset FROM equipment.equipments LIMIT 1"))
            print("✅ [PASS] is_fixed_asset 字段存在")
        except Exception as e:
            print(f"❌ [FAIL] is_fixed_asset 字段缺失: {e}")
            return False

        # 2. 检查 equipment_tag 唯一索引
        result = await db.execute(text("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname = 'equipment' AND tablename = 'equipments' AND indexname = 'uq_equipments_equipment_tag'
        """))
        if result.scalar():
            print("✅ [PASS] uq_equipments_equipment_tag 索引存在")
        else:
            print("❌ [FAIL] uq_equipments_equipment_tag 索引缺失")
            return False

        # 3. 检查审计日志表
        try:
            await db.execute(text("SELECT batch_id FROM equipment.import_audit_logs LIMIT 1"))
            print("✅ [PASS] import_audit_logs 表存在")
        except Exception as e:
            print(f"❌ [FAIL] import_audit_logs 表缺失: {e}")
            return False

        print("\n🎉 所有迁移验证通过！")
        return True

if __name__ == "__main__":
    success = asyncio.run(verify())
    sys.exit(0 if success else 1)
