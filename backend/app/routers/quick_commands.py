"""Quick Commands — 快捷命令 CRUD（所有机器共享）"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app import models
from app.auth import get_current_user

router = APIRouter(prefix="/api/quick-commands", tags=["快捷命令"])


class QuickCommandCreate(BaseModel):
    name: str
    command: str
    category: str = "默认分类"
    sort_order: int = 0


class QuickCommandUpdate(BaseModel):
    name: str | None = None
    command: str | None = None
    category: str | None = None
    sort_order: int | None = None


@router.get("")
async def list_commands(user: models.User = Depends(get_current_user)):
    """获取当前用户的所有快捷命令"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.QuickCommand)
            .where(models.QuickCommand.owner_id == user.id)
            .order_by(models.QuickCommand.category, models.QuickCommand.sort_order, models.QuickCommand.id)
        )
        commands = result.scalars().all()
        return [
            {"id": c.id, "name": c.name, "command": c.command, "category": c.category, "sort_order": c.sort_order}
            for c in commands
        ]


@router.post("")
async def create_command(params: QuickCommandCreate, user: models.User = Depends(get_current_user)):
    """创建快捷命令"""
    async with AsyncSessionLocal() as db:
        cmd = models.QuickCommand(
            owner_id=user.id,
            name=params.name,
            command=params.command,
            category=params.category,
            sort_order=params.sort_order,
        )
        db.add(cmd)
        await db.commit()
        await db.refresh(cmd)
        return {"id": cmd.id, "name": cmd.name, "command": cmd.command, "category": cmd.category, "sort_order": cmd.sort_order}


@router.put("/{cmd_id}")
async def update_command(cmd_id: int, params: QuickCommandUpdate, user: models.User = Depends(get_current_user)):
    """更新快捷命令"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.QuickCommand)
            .where(models.QuickCommand.id == cmd_id, models.QuickCommand.owner_id == user.id)
        )
        cmd = result.scalar_one_or_none()
        if not cmd:
            raise HTTPException(status_code=404, detail="命令不存在")
        if params.name is not None:
            cmd.name = params.name
        if params.command is not None:
            cmd.command = params.command
        if params.category is not None:
            cmd.category = params.category
        if params.sort_order is not None:
            cmd.sort_order = params.sort_order
        await db.commit()
        return {"id": cmd.id, "name": cmd.name, "command": cmd.command, "category": cmd.category, "sort_order": cmd.sort_order}


@router.delete("/{cmd_id}")
async def delete_command(cmd_id: int, user: models.User = Depends(get_current_user)):
    """删除快捷命令"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.QuickCommand)
            .where(models.QuickCommand.id == cmd_id, models.QuickCommand.owner_id == user.id)
        )
        cmd = result.scalar_one_or_none()
        if not cmd:
            raise HTTPException(status_code=404, detail="命令不存在")
        await db.delete(cmd)
        await db.commit()
        return {"message": "已删除"}
