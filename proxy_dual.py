# -*- coding: utf-8 -*-
# tcp mapping created by Wvfly at 2025-04-24
# Updated with IPv4/IPv6 dual stack support

import sys
import socket
import logging
import threading
from logging.handlers import RotatingFileHandler

配置参数
CFG_REMOTE_IP = sys.argv[1]
CFG_REMOTE_PORT = int(sys.argv[2])
CFG_LOCAL_IP = '::'  # 监听所有IPv6/IPv4地址
CFG_LOCAL_PORT = int(sys.argv[3])

# 网络参数
PKT_BUFF_SIZE = 2048
CONN_TIMEOUT = 30  # 秒

logger = logging.getLogger("Proxy Logging")
def setup_logger():
    """配置日志记录器"""
    formatter = logging.Formatter(
        '%(name)-12s %(asctime)s %(levelname)-8s %(lineno)-4d %(message)s',
        '%Y %b %d %a %H:%M:%S'
    )

    # 控制台日志
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)

    # 文件日志（自动轮换）
    file_handler = RotatingFileHandler(
        filename="proxy.log",
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)


def enable_dual_stack(sock):
    """启用IPv4/IPv6双栈支持"""
    try:
        # 关键设置：允许IPv4连接通过IPv6 socket
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        return True
    except AttributeError:
        logger.warning("IPV6_V6ONLY option not supported")
    except OSError as e:
        if e.errno == 10042:  # Windows错误码
            logger.warning("Dual stack not supported on Windows")
        else:
            logger.error(f"Socket option error: {str(e)}")
    return False


def tcp_mapping_worker(conn_recv, conn_send):
    """单向数据流处理"""
    try:
        while True:
            data = conn_recv.recv(PKT_BUFF_SIZE)
            if not data:
                logger.debug("Connection closed gracefully")
                break

            try:
                conn_send.sendall(data)
            except (BrokenPipeError, ConnectionResetError):
                logger.error("Remote connection broken")
                break

            # 日志优化：显示友好IP格式
            src = format_address(conn_recv.getpeername())
            dst = format_address(conn_send.getpeername())
            logger.info(f"Transfer {len(data)} bytes: {src} -> {dst}")

    except socket.timeout:
        logger.warning("Connection timeout")
    except Exception as e:
        logger.error(f"Data transfer error: {str(e)}")
    finally:
        conn_recv.close()
        conn_send.close()


def format_address(address):
    """将地址转换为友好格式"""
    ip, port, *rest = address
    if ip.startswith('::ffff:'):
        return f"{ip[7:]}:{port} (IPv4)"
    return f"[{ip}]:{port}" if ':' in ip else f"{ip}:{port}"


def tcp_mapping_request(local_conn, remote_host, remote_port):
    """处理客户端连接"""
    remote_conn = None
    try:
        # 动态解析目标地址协议
        addr_info = socket.getaddrinfo(
            remote_host, remote_port,
            proto=socket.IPPROTO_TCP,
            type=socket.SOCK_STREAM,
            flags=socket.AI_ADDRCONFIG
        )
        if not addr_info:
            logger.error(f"Cannot resolve {remote_host}:{remote_port}")
            return

        # 创建与目标协议匹配的socket
        family, socktype, proto, _, sockaddr = addr_info[0]
        remote_conn = socket.socket(family, socktype, proto)

        # 跨平台KeepAlive设置
        if sys.platform.startswith('win'):
            remote_conn.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 30 * 1000, 5 * 1000))
        else:
            remote_conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            remote_conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
            remote_conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
            remote_conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 2)

        remote_conn.settimeout(CONN_TIMEOUT)
        remote_conn.connect(sockaddr)
        logger.debug(f"Connected to remote: {format_address(sockaddr)}")

        # 启动双向数据传输
        threading.Thread(
            target=tcp_mapping_worker,
            args=(local_conn, remote_conn),
            daemon=True
        ).start()
        threading.Thread(
            target=tcp_mapping_worker,
            args=(remote_conn, local_conn),
            daemon=True
        ).start()

    except Exception as e:
        logger.error(f"Connection failed: {str(e)}")
        if remote_conn:
            remote_conn.close()
        local_conn.close()


def start_proxy_server():
    """启动双栈代理服务"""
    server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # 关键双栈配置
    if enable_dual_stack(server):
        logger.debug("Dual stack listening enabled")
    else:
        logger.warning("Running in IPv6-only mode")

    # 跨平台KeepAlive设置
    if sys.platform.startswith('win'):
        server.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 30 * 1000, 5 * 1000))
    else:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        server.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
        server.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
        server.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 2)

    try:
        server.bind((CFG_LOCAL_IP, CFG_LOCAL_PORT))
        server.listen(5)
        logger.info(f"Listening on [{CFG_LOCAL_IP}]:{CFG_LOCAL_PORT}")
        logger.info(f"Mapping to -> {CFG_REMOTE_IP}:{CFG_REMOTE_PORT}")

        while True:
            client_conn, client_addr = server.accept()
            client_conn.settimeout(CONN_TIMEOUT)

            # 日志优化显示客户端地址
            logger.debug(f"New connection: {format_address(client_addr)}")

            threading.Thread(
                target=tcp_mapping_request,
                args=(client_conn, CFG_REMOTE_IP, CFG_REMOTE_PORT),
                daemon=True
            ).start()

    except KeyboardInterrupt:
        logger.info("Server shutdown by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
    finally:
        server.close()
        logger.info("Service stopped")


if __name__ == '__main__':
    setup_logger()
    try:
        start_proxy_server()
    except Exception as e:
        logger.critical(f"Startup failed: {str(e)}")
        sys.exit(1)
