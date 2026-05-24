"""Web SSH Terminal — WebSocket + Paramiko"""
import asyncio
import io
import json
import logging
import paramiko
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.database import AsyncSessionLocal
from app import models
from app.config import settings
from jose import JWTError, jwt
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/terminal", tags=["Web终端"])


async def _authenticate_ws(token: str) -> models.User:
    """从 token 验证 WebSocket 用户"""
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


@router.websocket("/ws")
async def websocket_ssh(
    websocket: WebSocket,
    token: str = Query(default=""),
    host: str = Query(default=""),
    port: int = Query(default=22),
    username: str = Query(default="root"),
    auth_type: str = Query(default="password"),
    tenant_id: int = Query(default=0),
):
    """
    WebSocket SSH 终端
    流程：
    1. 通过 query params 传递基本连接信息
    2. WebSocket 建立后，前端发送第一条消息包含认证凭据（密码或私钥）
    3. 后端用 paramiko 建立 SSH 连接
    4. 之后双向转发数据
    """
    await websocket.accept()

    # 1. 验证用户身份
    user = await _authenticate_ws(token)
    if not user:
        await websocket.send_text("\r\n\x1b[31m认证失败，请重新登录\x1b[0m\r\n")
        await websocket.close()
        return

    if not host:
        await websocket.send_text("\r\n\x1b[31m未指定目标主机\x1b[0m\r\n")
        await websocket.close()
        return

    # 2. 等待前端发送认证信息
    try:
        auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=30)
        auth_data = json.loads(auth_msg)
    except asyncio.TimeoutError:
        await websocket.send_text("\r\n\x1b[31m等待认证信息超时\x1b[0m\r\n")
        await websocket.close()
        return
    except Exception:
        await websocket.send_text("\r\n\x1b[31m认证信息格式错误\x1b[0m\r\n")
        await websocket.close()
        return

    credential_auth_type = auth_data.get("auth_type", auth_type)
    password = auth_data.get("password", "")
    private_key_str = auth_data.get("private_key", "")

    # 3. 建立 SSH 连接
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    await websocket.send_text(f"\r\n\x1b[33m正在连接 {username}@{host}:{port} ...\x1b[0m\r\n")

    try:
        loop = asyncio.get_event_loop()

        if credential_auth_type == "key" and private_key_str:
            # 尝试多种私钥格式
            pkey = None
            for key_class in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey):
                try:
                    pkey = key_class.from_private_key(io.StringIO(private_key_str))
                    break
                except Exception:
                    continue
            if not pkey:
                await websocket.send_text("\r\n\x1b[31m私钥格式无法识别，支持 RSA/Ed25519/ECDSA\x1b[0m\r\n")
                await websocket.close()
                return

            await loop.run_in_executor(
                None,
                lambda: ssh_client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    pkey=pkey,
                    timeout=15,
                    look_for_keys=False,
                    allow_agent=False,
                )
            )
        else:
            # 密码认证
            await loop.run_in_executor(
                None,
                lambda: ssh_client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=15,
                    look_for_keys=False,
                    allow_agent=False,
                )
            )

        await websocket.send_text(f"\r\n\x1b[32m已连接到 {host}\x1b[0m\r\n\r\n")

    except paramiko.AuthenticationException:
        await websocket.send_text("\r\n\x1b[31mSSH 认证失败：用户名/密码错误或私钥不匹配\x1b[0m\r\n")
        await websocket.close()
        return
    except paramiko.ssh_exception.NoValidConnectionsError:
        await websocket.send_text(f"\r\n\x1b[31m无法连接到 {host}:{port}，请检查主机是否可达\x1b[0m\r\n")
        await websocket.close()
        return
    except Exception as e:
        await websocket.send_text(f"\r\n\x1b[31mSSH 连接失败: {str(e)}\x1b[0m\r\n")
        await websocket.close()
        return

    # 4. 打开交互式 shell
    try:
        channel = ssh_client.invoke_shell(term="xterm-256color", width=120, height=40)
    except Exception as e:
        await websocket.send_text(f"\r\n\x1b[31m打开 Shell 失败: {str(e)}\x1b[0m\r\n")
        ssh_client.close()
        await websocket.close()
        return

    # 5. 双向转发
    async def read_from_ssh():
        """从 SSH channel 读取数据发送到 WebSocket"""
        import socket
        loop = asyncio.get_event_loop()
        while not channel.closed:
            try:
                # 使用短超时的阻塞读取，避免长时间占用线程
                channel.settimeout(0.5)
                data = await loop.run_in_executor(None, lambda: channel.recv(4096))
                if not data:
                    break
                await websocket.send_text(data.decode("utf-8", errors="replace"))
            except socket.timeout:
                continue
            except paramiko.ssh_exception.SSHException:
                break
            except OSError:
                break
            except Exception:
                continue

    async def read_from_ws():
        """从 WebSocket 读取数据发送到 SSH channel"""
        while True:
            try:
                data = await websocket.receive_text()
                # 处理终端大小调整
                if data.startswith("\x1b[RESIZE:"):
                    try:
                        parts = data.replace("\x1b[RESIZE:", "").replace("]", "").split(",")
                        cols, rows = int(parts[0]), int(parts[1])
                        channel.resize_pty(width=cols, height=rows)
                    except Exception:
                        pass
                else:
                    channel.send(data)
            except WebSocketDisconnect:
                break
            except Exception:
                break

    # 并发运行两个方向的转发
    try:
        await asyncio.gather(
            read_from_ssh(),
            read_from_ws(),
            return_exceptions=True,
        )
    finally:
        channel.close()
        ssh_client.close()
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/ws/console")
async def websocket_console_ssh(
    websocket: WebSocket,
    token: str = Query(default=""),
):
    """
    WebSocket Console SSH 终端（用于 OCI 串行控制台）
    通过系统 SSH 命令 + ProxyCommand 连接，因为 Paramiko 不支持 ProxyCommand。
    前端发送第一条消息包含 ssh_connection_string 和 private_key。
    """
    import tempfile
    import os

    await websocket.accept()

    user = await _authenticate_ws(token)
    if not user:
        await websocket.send_text("\r\n\x1b[31m认证失败，请重新登录\x1b[0m\r\n")
        await websocket.close()
        return

    # 等待前端发送连接信息
    try:
        auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=30)
        auth_data = json.loads(auth_msg)
    except asyncio.TimeoutError:
        await websocket.send_text("\r\n\x1b[31m等待连接信息超时\x1b[0m\r\n")
        await websocket.close()
        return
    except Exception:
        await websocket.send_text("\r\n\x1b[31m连接信息格式错误\x1b[0m\r\n")
        await websocket.close()
        return

    ssh_connection_string = auth_data.get("ssh_connection_string", "")
    private_key = auth_data.get("private_key", "")

    if not ssh_connection_string or not private_key:
        await websocket.send_text("\r\n\x1b[31m缺少连接字符串或私钥\x1b[0m\r\n")
        await websocket.close()
        return

    # 将私钥写入临时文件
    key_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
    key_file.write(private_key)
    key_file.close()
    os.chmod(key_file.name, 0o600)

    # 修改 SSH 命令：替换密钥路径，添加必要参数
    # OCI 的 ssh_connection_string 格式:
    # ssh -o ProxyCommand='ssh -W %h:%p -p 443 ocid1...' ocid1.instance...
    # 需要加上 -i key_file -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null
    ssh_cmd = ssh_connection_string.strip()
    # 在 ssh 后面插入参数
    if ssh_cmd.startswith("ssh "):
        extra_opts = (
            f"-tt -i {key_file.name} "
            "-o StrictHostKeyChecking=no "
            "-o UserKnownHostsFile=/dev/null "
            "-o HostKeyAlgorithms=+ssh-rsa "
            "-o PubkeyAcceptedAlgorithms=+ssh-rsa "
        )
        ssh_cmd = "ssh " + extra_opts + ssh_cmd[4:]
        # ProxyCommand 里的 ssh 也需要加参数
        ssh_cmd = ssh_cmd.replace(
            "ProxyCommand='ssh ",
            f"ProxyCommand='ssh -i {key_file.name} "
            "-o StrictHostKeyChecking=no "
            "-o UserKnownHostsFile=/dev/null "
            "-o HostKeyAlgorithms=+ssh-rsa "
            "-o PubkeyAcceptedAlgorithms=+ssh-rsa "
        )

    await websocket.send_text(f"\r\n\x1b[33m正在连接 OCI 串行控制台...\x1b[0m\r\n")

    try:
        process = await asyncio.create_subprocess_shell(
            ssh_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except Exception as e:
        await websocket.send_text(f"\r\n\x1b[31m启动 SSH 进程失败: {str(e)}\x1b[0m\r\n")
        os.unlink(key_file.name)
        await websocket.close()
        return

    await websocket.send_text(f"\r\n\x1b[32m已连接\x1b[0m\r\n")

    async def read_from_process():
        """从 SSH 进程读取输出发送到 WebSocket"""
        while True:
            try:
                data = await process.stdout.read(4096)
                if not data:
                    break
                await websocket.send_text(data.decode("utf-8", errors="replace"))
            except Exception:
                break

    async def read_from_ws():
        """从 WebSocket 读取输入发送到 SSH 进程"""
        while True:
            try:
                data = await websocket.receive_text()
                if process.stdin:
                    process.stdin.write(data.encode("utf-8"))
                    await process.stdin.drain()
            except (WebSocketDisconnect, Exception):
                break

    try:
        await asyncio.gather(read_from_process(), read_from_ws(), return_exceptions=True)
    finally:
        process.kill()
        os.unlink(key_file.name)
        try:
            await websocket.close()
        except Exception:
            pass
