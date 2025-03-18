# -*- coding: utf-8 -*-
# tcp mapping created by Wvfly at 2023-06-20

import sys
import socket
import logging
import threading
from logging.handlers import RotatingFileHandler

# 端口映射配置信息
CFG_REMOTE_IP = sys.argv[1]
CFG_REMOTE_PORT = int(sys.argv[2])
CFG_LOCAL_IP = '0.0.0.0'
CFG_LOCAL_PORT = int(sys.argv[3])

# 接收数据缓存大小
PKT_BUFF_SIZE = 2048

logger = logging.getLogger("Proxy Logging")
formatter = logging.Formatter('%(name)-12s %(asctime)s %(levelname)-8s %(lineno)-4d %(message)s',
                              '%Y %b %d %a %H:%M:%S', )

stream_handler = logging.StreamHandler(sys.stderr)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

file_handler = RotatingFileHandler(
    filename="proxy.log",  # 日志文件名
    maxBytes=100 * 1024 * 1024,  # 单个文件最大 100MB（按需调整）
    backupCount=5,  # 保留 5 个归档文件
    encoding="utf-8"  # 可选：指定编码
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.setLevel(logging.DEBUG)


# 单向流数据传递
def tcp_mapping_worker(conn_receiver, conn_sender):
    while True:
        try:
            data = conn_receiver.recv(PKT_BUFF_SIZE)
        except Exception:
            logger.debug('Connection closed.')
            break

        if not data:
            logger.info('No more data is received.')
            break

        try:
            conn_sender.sendall(data)
        except Exception:
            logger.error('Failed sending data.')
            break

        # logger.info('Mapping data > %s ' % repr(data))
        logger.info(
            'Mapping > %s -> %s > %d bytes.' % (conn_receiver.getpeername(), conn_sender.getpeername(), len(data)))

    conn_receiver.close()
    conn_sender.close()

    return


# 端口映射请求处理
def tcp_mapping_request(local_conn, remote_ip, remote_port):
    remote_conn = None
    try:
        remote_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 跨平台KeepAlive设置
        if sys.platform.startswith('win'):
            remote_conn.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 30 * 1000, 5 * 1000))
        else:
            remote_conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            remote_conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
            remote_conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
            remote_conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 2)

        remote_conn.settimeout(30.0)
        remote_conn.connect((remote_ip, remote_port))

        # 添加双连接状态监控
        threading.Thread(target=tcp_mapping_worker, args=(local_conn, remote_conn), daemon=True).start()
        threading.Thread(target=tcp_mapping_worker, args=(remote_conn, local_conn), daemon=True).start()

    except Exception as e:
        logger.error(f'Connection failed: {str(e)}')
        if remote_conn:
            remote_conn.close()
        local_conn.close()


# 端口映射函数
def tcp_mapping(remote_ip, remote_port, local_ip, local_port):
    local_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    local_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # 设置 Keepalive 参数（Linux 有效）
    if sys.platform.startswith('win'):
        local_server.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 30 * 1000, 5 * 1000))
    else:
        local_server.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        local_server.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
        local_server.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
        local_server.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 2)
    local_server.bind((local_ip, local_port))
    local_server.listen(5)

    logger.debug(f'Starting mapping service on {local_ip}:{local_port} ...')
    logger.debug('Client timeout was set to 30s.')

    try:
        while True:
            local_conn, local_addr = local_server.accept()
            logger.debug(f'Receive mapping request from {local_addr}.')
            try:
                # 设置客户端 Socket 超时
                local_conn.settimeout(30.0)
                # 启动线程处理连接
                threading.Thread(
                    target=tcp_mapping_request,
                    args=(local_conn, remote_ip, remote_port),
                    daemon=True  # 设置为守护线程，防止主线程退出阻塞
                ).start()
            except Exception as e:
                logger.error(f"Error handling connection: {e}")
                local_conn.close()  # 确保异常时关闭连接
    except KeyboardInterrupt:
        logger.debug("Server shutdown by user.")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        local_server.close()
        logger.debug('Stop mapping service.')


# 主函数
if __name__ == '__main__':
    tcp_mapping(CFG_REMOTE_IP, CFG_REMOTE_PORT, CFG_LOCAL_IP, CFG_LOCAL_PORT)