"""Terminal System Monitor & File Manager — SSH-based system info + SFTP"""
import asyncio
import io
import json
import logging
import stat
import paramiko
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.database import AsyncSessionLocal
from app import models
from app.auth import get_current_user
from app.config import settings
from jose import JWTError, jwt
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/terminal-monitor", tags=["终端监控"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _authenticate_ws(token: str) -> Optional[models.User]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username = payload.get("sub")
        if not username:
            return None
    except JWTError:
        return None
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.User).where(models.User.username == username)
        )
        return result.scalar_one_or_none()


def _connect_ssh(host: str, port: int, username: str, auth_type: str,
                 password: str = "", private_key_str: str = "") -> paramiko.SSHClient:
    """建立 SSH 连接（同步，需在 executor 中调用）"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if auth_type == "key" and private_key_str:
        pkey = None
        for key_class in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey):
            try:
                pkey = key_class.from_private_key(io.StringIO(private_key_str))
                break
            except Exception:
                continue
        if not pkey:
            raise ValueError("私钥格式无法识别")
        ssh.connect(hostname=host, port=port, username=username, pkey=pkey,
                    timeout=10, look_for_keys=False, allow_agent=False)
    else:
        ssh.connect(hostname=host, port=port, username=username, password=password,
                    timeout=10, look_for_keys=False, allow_agent=False)
    return ssh


def _exec_cmd(ssh: paramiko.SSHClient, cmd: str, timeout: int = 5) -> str:
    """执行命令并返回 stdout"""
    _, stdout, _ = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode("utf-8", errors="replace").strip()


def _parse_system_info(ssh: paramiko.SSHClient) -> dict:
    """通过一次性执行多个命令获取系统信息"""
    # 合并多个命令减少 SSH 往返
    combined_cmd = " && ".join([
        "echo '===UPTIME==='", "cat /proc/uptime",
        "echo '===LOADAVG==='", "cat /proc/loadavg",
        "echo '===CPU==='", "grep -c ^processor /proc/cpuinfo",
        "echo '===CPUSTAT==='", "head -1 /proc/stat",
        "echo '===MEM==='", "cat /proc/meminfo",
        "echo '===NET==='", "cat /proc/net/dev",
        "echo '===DISK==='", "df -B1 2>/dev/null || df -k",
        "echo '===PROCS==='", "echo '---MEM---' && ps aux --sort=-%mem 2>/dev/null | awk 'NR>1{print $6,$3,$11}' | head -2 && echo '---CPU---' && ps aux --sort=-%cpu 2>/dev/null | awk 'NR>1{print $6,$3,$11}' | head -2",
        "echo '===HOSTNAME==='", "hostname",
    ])

    output = _exec_cmd(ssh, combined_cmd, timeout=8)
    sections = {}
    current_key = None
    current_lines = []

    for line in output.split("\n"):
        if line.startswith("===") and line.endswith("==="):
            if current_key:
                sections[current_key] = "\n".join(current_lines)
            current_key = line.strip("=")
            current_lines = []
        else:
            current_lines.append(line)
    if current_key:
        sections[current_key] = "\n".join(current_lines)

    result = {
        "hostname": sections.get("HOSTNAME", "").strip(),
        "uptime_seconds": 0,
        "load_avg": [0, 0, 0],
        "cpu_cores": 1,
        "cpu_percent": 0,
        "memory": {"total": 0, "used": 0, "free": 0, "percent": 0},
        "swap": {"total": 0, "used": 0, "free": 0, "percent": 0},
        "network": [],
        "disks": [],
        "processes": [],
    }

    # Uptime
    try:
        result["uptime_seconds"] = int(float(sections.get("UPTIME", "0").split()[0]))
    except Exception:
        pass

    # Load average
    try:
        parts = sections.get("LOADAVG", "").split()
        result["load_avg"] = [float(parts[0]), float(parts[1]), float(parts[2])]
    except Exception:
        pass

    # CPU cores
    try:
        result["cpu_cores"] = int(sections.get("CPU", "1"))
    except Exception:
        pass

    # CPU usage from /proc/stat (rough estimate)
    try:
        cpu_line = sections.get("CPUSTAT", "")
        parts = cpu_line.split()
        if len(parts) >= 8:
            user, nice, system, idle, iowait = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
            total = user + nice + system + idle + iowait
            busy = user + nice + system
            result["cpu_percent"] = round(busy / total * 100, 1) if total > 0 else 0
    except Exception:
        pass

    # Memory
    try:
        meminfo = sections.get("MEM", "")
        mem = {}
        for line in meminfo.split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                # 值通常是 "12345 kB"
                num = int(val.strip().split()[0]) * 1024  # kB -> bytes
                mem[key.strip()] = num
        total = mem.get("MemTotal", 0)
        available = mem.get("MemAvailable", mem.get("MemFree", 0))
        used = total - available
        result["memory"] = {
            "total": total,
            "used": used,
            "free": available,
            "percent": round(used / total * 100, 1) if total > 0 else 0,
        }
        swap_total = mem.get("SwapTotal", 0)
        swap_free = mem.get("SwapFree", 0)
        swap_used = swap_total - swap_free
        result["swap"] = {
            "total": swap_total,
            "used": swap_used,
            "free": swap_free,
            "percent": round(swap_used / swap_total * 100, 1) if swap_total > 0 else 0,
        }
    except Exception:
        pass

    # Network interfaces
    try:
        net_lines = sections.get("NET", "").split("\n")
        for line in net_lines[2:]:  # skip header lines
            if ":" not in line:
                continue
            iface, data = line.split(":", 1)
            iface = iface.strip()
            if iface == "lo":
                continue
            parts = data.split()
            if len(parts) >= 9:
                result["network"].append({
                    "interface": iface,
                    "rx_bytes": int(parts[0]),
                    "tx_bytes": int(parts[8]),
                })
    except Exception:
        pass

    # Disks (include all mounted filesystems, sorted by total size desc)
    try:
        disk_lines = sections.get("DISK", "").split("\n")
        for line in disk_lines[1:]:  # skip header
            parts = line.split()
            if len(parts) >= 6:
                # Skip pseudo filesystems with 0 total
                try:
                    total = int(parts[1])
                except ValueError:
                    continue
                if total == 0:
                    continue
                result["disks"].append({
                    "filesystem": parts[0],
                    "total": total,
                    "used": int(parts[2]),
                    "available": int(parts[3]),
                    "mount": parts[5],
                })
        # Sort by total size descending
        result["disks"].sort(key=lambda d: d["total"], reverse=True)
    except Exception:
        pass

    # Processes (top 2 by memory + top 2 by CPU)
    try:
        proc_text = sections.get("PROCS", "")
        mem_procs = []
        cpu_procs = []
        current_list = None
        for line in proc_text.split("\n"):
            if line.strip() == "---MEM---":
                current_list = mem_procs
                continue
            elif line.strip() == "---CPU---":
                current_list = cpu_procs
                continue
            if current_list is None:
                continue
            parts = line.split(None, 2)
            if len(parts) >= 3:
                try:
                    rss_kb = int(parts[0])
                    cpu_pct = float(parts[1])
                except ValueError:
                    continue
                cmd = parts[2].split("/")[-1][:20]
                current_list.append({
                    "rss": rss_kb * 1024,
                    "cpu": cpu_pct,
                    "command": cmd,
                })
        # Deduplicate: if a CPU top process is already in mem list, skip it
        mem_cmds = {p["command"] for p in mem_procs}
        cpu_deduped = [p for p in cpu_procs if p["command"] not in mem_cmds]
        result["processes"] = mem_procs[:2] + (cpu_deduped[:2] if len(cpu_deduped) >= 2 else cpu_procs[:2])
    except Exception:
        pass

    return result


# ─── WebSocket: System Monitor ────────────────────────────────────────────────

@router.websocket("/ws/monitor")
async def websocket_monitor(
    websocket: WebSocket,
    token: str = Query(default=""),
    host: str = Query(default=""),
    port: int = Query(default=22),
    username: str = Query(default="root"),
    auth_type: str = Query(default="password"),
):
    """
    WebSocket 系统监控
    连接后前端发送认证信息，之后后端每 2 秒推送系统信息
    """
    await websocket.accept()

    user = await _authenticate_ws(token)
    if not user:
        await websocket.send_text(json.dumps({"error": "认证失败"}))
        await websocket.close()
        return

    # 等待认证信息
    try:
        auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=30)
        auth_data = json.loads(auth_msg)
    except Exception:
        await websocket.send_text(json.dumps({"error": "认证信息超时或格式错误"}))
        await websocket.close()
        return

    password = auth_data.get("password", "")
    private_key_str = auth_data.get("private_key", "")

    # 建立 SSH 连接
    loop = asyncio.get_event_loop()
    try:
        ssh = await loop.run_in_executor(
            None,
            lambda: _connect_ssh(host, port, username, auth_type, password, private_key_str)
        )
    except Exception as e:
        await websocket.send_text(json.dumps({"error": f"SSH 连接失败: {str(e)}"}))
        await websocket.close()
        return

    # 保存上一次网络数据用于计算速率
    prev_net = {}

    async def ping_host() -> float:
        """测量到远程主机的延迟 ms，失败返回 -1
        优先用 ICMP ping，失败则用 TCP 连接 SSH 端口测延迟"""
        import time

        # 先尝试 ICMP ping
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c", "1", "-W", "1", host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2)
            output = stdout.decode()
            for part in output.split():
                if part.startswith("time="):
                    return float(part.split("=")[1])
        except Exception:
            pass

        # 回退：TCP 连接测延迟
        try:
            start = time.monotonic()
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=2
            )
            elapsed = (time.monotonic() - start) * 1000  # ms
            writer.close()
            await writer.wait_closed()
            return round(elapsed, 1)
        except Exception:
            return -1

    async def push_info():
        nonlocal prev_net
        while True:
            try:
                # 并发执行系统信息采集和 ping
                info_task = loop.run_in_executor(None, lambda: _parse_system_info(ssh))
                ping_task = ping_host()
                info, ping_ms = await asyncio.gather(info_task, ping_task)

                # 计算网络速率（每秒）
                for iface in info["network"]:
                    name = iface["interface"]
                    if name in prev_net:
                        iface["rx_rate"] = max(0, iface["rx_bytes"] - prev_net[name]["rx"])
                        iface["tx_rate"] = max(0, iface["tx_bytes"] - prev_net[name]["tx"])
                    else:
                        iface["rx_rate"] = 0
                        iface["tx_rate"] = 0
                    prev_net[name] = {"rx": iface["rx_bytes"], "tx": iface["tx_bytes"]}

                info["ping_ms"] = ping_ms  # -1 表示丢包

                await websocket.send_text(json.dumps(info))
                await asyncio.sleep(1)
            except (WebSocketDisconnect, Exception):
                break

    async def listen_ws():
        """监听前端消息（如断开信号）"""
        while True:
            try:
                await websocket.receive_text()
            except (WebSocketDisconnect, Exception):
                break

    try:
        await asyncio.gather(push_info(), listen_ws(), return_exceptions=True)
    finally:
        ssh.close()
        try:
            await websocket.close()
        except Exception:
            pass


# ─── REST: File Manager (SFTP) ────────────────────────────────────────────────

class FileListRequest(BaseModel):
    host: str
    port: int = 22
    username: str = "root"
    auth_type: str = "password"
    password: str = ""
    private_key: str = ""
    path: str = "/"


class FileActionRequest(BaseModel):
    host: str
    port: int = 22
    username: str = "root"
    auth_type: str = "password"
    password: str = ""
    private_key: str = ""
    path: str
    new_path: str = ""  # for rename/move


def _get_sftp(req) -> tuple[paramiko.SSHClient, paramiko.SFTPClient]:
    ssh = _connect_ssh(req.host, req.port, req.username, req.auth_type,
                       req.password, req.private_key)
    sftp = ssh.open_sftp()
    return ssh, sftp


@router.post("/files/list")
async def list_files(req: FileListRequest, user: models.User = Depends(get_current_user)):
    """列出目录内容"""
    loop = asyncio.get_event_loop()
    try:
        ssh, sftp = await loop.run_in_executor(None, lambda: _get_sftp(req))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接失败: {str(e)}")

    try:
        entries = await loop.run_in_executor(None, lambda: sftp.listdir_attr(req.path))
        files = []
        for entry in entries:
            is_dir = stat.S_ISDIR(entry.st_mode) if entry.st_mode else False
            is_link = stat.S_ISLNK(entry.st_mode) if entry.st_mode else False
            files.append({
                "name": entry.filename,
                "is_dir": is_dir,
                "is_link": is_link,
                "size": entry.st_size or 0,
                "mtime": entry.st_mtime or 0,
                "permissions": oct(entry.st_mode & 0o777) if entry.st_mode else "0000",
                "uid": entry.st_uid,
                "gid": entry.st_gid,
            })
        # 排序：目录在前，然后按名称
        files.sort(key=lambda f: (not f["is_dir"], f["name"].lower()))
        return {"path": req.path, "files": files}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"列出目录失败: {str(e)}")
    finally:
        sftp.close()
        ssh.close()


@router.post("/files/mkdir")
async def mkdir(req: FileActionRequest, user: models.User = Depends(get_current_user)):
    """创建目录"""
    loop = asyncio.get_event_loop()
    try:
        ssh, sftp = await loop.run_in_executor(None, lambda: _get_sftp(req))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接失败: {str(e)}")
    try:
        await loop.run_in_executor(None, lambda: sftp.mkdir(req.path))
        return {"message": "目录创建成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建目录失败: {str(e)}")
    finally:
        sftp.close()
        ssh.close()


@router.post("/files/delete")
async def delete_file(req: FileActionRequest, user: models.User = Depends(get_current_user)):
    """删除文件或目录"""
    loop = asyncio.get_event_loop()
    try:
        ssh, sftp = await loop.run_in_executor(None, lambda: _get_sftp(req))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接失败: {str(e)}")
    try:
        file_stat = await loop.run_in_executor(None, lambda: sftp.stat(req.path))
        if stat.S_ISDIR(file_stat.st_mode):
            # 递归删除目录用 rm -rf
            await loop.run_in_executor(None, lambda: _exec_cmd(ssh, f"rm -rf '{req.path}'"))
        else:
            await loop.run_in_executor(None, lambda: sftp.remove(req.path))
        return {"message": "删除成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"删除失败: {str(e)}")
    finally:
        sftp.close()
        ssh.close()


@router.post("/files/rename")
async def rename_file(req: FileActionRequest, user: models.User = Depends(get_current_user)):
    """重命名/移动文件"""
    loop = asyncio.get_event_loop()
    if not req.new_path:
        raise HTTPException(status_code=400, detail="缺少 new_path")
    try:
        ssh, sftp = await loop.run_in_executor(None, lambda: _get_sftp(req))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接失败: {str(e)}")
    try:
        await loop.run_in_executor(None, lambda: sftp.rename(req.path, req.new_path))
        return {"message": "重命名成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"重命名失败: {str(e)}")
    finally:
        sftp.close()
        ssh.close()


@router.post("/files/download")
async def download_file(req: FileActionRequest, user: models.User = Depends(get_current_user)):
    """下载文件"""
    loop = asyncio.get_event_loop()
    try:
        ssh, sftp = await loop.run_in_executor(None, lambda: _get_sftp(req))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接失败: {str(e)}")

    try:
        file_stat = await loop.run_in_executor(None, lambda: sftp.stat(req.path))
        if stat.S_ISDIR(file_stat.st_mode):
            raise HTTPException(status_code=400, detail="不能下载目录")

        # 读取文件到内存
        buf = io.BytesIO()
        await loop.run_in_executor(None, lambda: sftp.getfo(req.path, buf))
        buf.seek(0)

        filename = req.path.split("/")[-1]
        return StreamingResponse(
            buf,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"下载失败: {str(e)}")
    finally:
        sftp.close()
        ssh.close()
