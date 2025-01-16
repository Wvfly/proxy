# -*- coding: utf-8 -*-
# Author : wuweigang
# 功能说明：应对公网服务器ssh爆破攻击，把ssh监听改为非22端口，然后启动本程序，把22端口的请求转发回给客户端。攻击我=攻击他自己

import sys
import socket
import logging
import threading

# 配置本地服务端口
CFG_LOCAL_IP = '0.0.0.0'
CFG_LOCAL_PORT = int(sys.argv[1])

# 接收数据缓存大小
PKT_BUFF_SIZE = 2048

logger = logging.getLogger("Proxy Logging")
formatter = logging.Formatter('%(name)-12s %(asctime)s %(levelname)-8s %(lineno)-4d %(message)s',
                              '%Y %b %d %a %H:%M:%S', )
stream_handler = logging.StreamHandler(sys.stderr)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


# 单向流数据传递
def tcp_mapping_worker(conn_receiver, conn_sender):
    while True:
        try:
            data = conn_receiver.recv(PKT_BUFF_SIZE)
        except socket.error as e:
            logger.debug(f"Connection closed due to socket error: {e}")
            break
        if not data:
            logger.info('No more data received, closing connection.')
            break
        try:
            conn_sender.sendall(data)
        except socket.error as e:
            logger.error(f"Failed sending data: {e}")
            break
        logger.info(f"Mapping {conn_receiver.getpeername()} -> {conn_sender.getpeername()} > {len(data)} bytes.")

    conn_receiver.close()
    conn_sender.close()


# 端口映射请求处理
def tcp_mapping_request(local_conn):
    # 获取客户端的 IP 地址，并将其用作远程服务器 IP，目标端口为 22
    remote_ip = local_conn.getpeername()[0]  # 获取客户端的 IP 地址
    remote_port = 22  # 目标端口 22 (SSH)

    remote_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        remote_conn.connect((remote_ip, remote_port))
    except socket.error as e:
        logger.error(f'Unable to connect to remote server {remote_ip}:{remote_port} - {e}')
        local_conn.close()
        return

    threading.Thread(target=tcp_mapping_worker, args=(local_conn, remote_conn), daemon=True).start()
    threading.Thread(target=tcp_mapping_worker, args=(remote_conn, local_conn), daemon=True).start()


# 端口映射函数
def tcp_mapping(local_ip, local_port):
    local_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    local_server.bind((local_ip, local_port))
    local_server.listen(5)
    logger.debug(f'Starting mapping service on {local_ip}:{local_port} ...')

    while True:
        try:
            local_conn, local_addr = local_server.accept()
            logger.debug(f'Received mapping request from {local_addr}')
            threading.Thread(target=tcp_mapping_request, args=(local_conn,), daemon=True).start()
        except Exception as e:
            logger.error(f"Error accepting connection: {e}")
            local_server.close()
            break


if __name__ == '__main__':
    tcp_mapping(CFG_LOCAL_IP, CFG_LOCAL_PORT)
