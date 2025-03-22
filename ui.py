import tkinter as tk
from tkinter import ttk, messagebox
import subprocess,psutil,threading,os,pystray
from PIL import Image

def kill_proc_tree(pid):
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except psutil.NoSuchProcess:
        pass

class ProxyController:
    def __init__(self):
        self.root = tk.Tk()
        self.proxy_running = False  # 初始代理状态
        self.proxy_process = None
        # self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        self.setup_ui()
        self.stop_event = threading.Event()

        self.tray_icon = None  # 托盘图标对象
        self.tray_icon_active = False  # 托盘图标是否已激活
        self.load_tray_icon()

        # 绑定窗口关闭事件（隐藏到托盘）
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)


    def setup_ui(self):
        self.root.title("TCP端口映射工具(Power by wuweigang)")
        self.root.geometry("600x400")

        # 输入框框架
        input_frame = ttk.Frame(self.root, padding="10 10 10 10")
        input_frame.pack(fill=tk.X)

        # 远程IP
        ttk.Label(input_frame, text="远程IP:").grid(row=0, column=0, sticky=tk.W)
        self.remote_ip = ttk.Entry(input_frame)
        self.remote_ip.grid(row=0, column=1, sticky=tk.EW)
        self.remote_ip.insert(0, "127.0.0.1")

        # 远程端口
        ttk.Label(input_frame, text="远程端口:").grid(row=1, column=0, sticky=tk.W)
        self.remote_port = ttk.Entry(input_frame)
        self.remote_port.grid(row=1, column=1, sticky=tk.EW)
        self.remote_port.insert(0, "80")

        # 本地端口
        ttk.Label(input_frame, text="本地端口:").grid(row=2, column=0, sticky=tk.W)
        self.local_port = ttk.Entry(input_frame)
        self.local_port.grid(row=2, column=1, sticky=tk.EW)
        self.local_port.insert(0, "8080")

        # 控制按钮
        self.btn = tk.Button(
            self.root,
            text="启动代理" if not self.proxy_running else "停止代理",
            command=self.toggle_proxy
        )
        self.btn.pack(padx=20, pady=20)

        # 日志框
        log_frame = ttk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log = tk.Text(log_frame, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)

        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 配置网格权重
        input_frame.columnconfigure(1, weight=1)

    def validate_inputs(self):
        try:
            remote_ip = self.remote_ip.get()
            remote_port = int(self.remote_port.get())
            local_port = int(self.local_port.get())

            if not 1 <= remote_port <= 65535:
                raise ValueError("远程端口无效")
            if not 1 <= local_port <= 65535:
                raise ValueError("本地端口无效")

            return remote_ip, remote_port, local_port

        except ValueError as e:
            messagebox.showerror("输入错误", f"参数错误: {str(e)}")
            return None

    def read_output(self):
        """读取子进程输出流的线程函数"""
        while not self.stop_event.is_set():
            if self.proxy_process is None:
                break  # 提前退出循环
            output = self.proxy_process.stdout.readline()
            # 原逻辑处理输出
            # if output == '' and self.proxy_process.poll() is not None:
            #     break
            if output:
                self.log.insert(tk.END, output)
                self.log.see(tk.END)

    def toggle_proxy(self):
        """切换代理状态的核心逻辑"""
        if self.proxy_running:
            self.stop_proxy()  # 执行停止代理操作
        else:
            params = self.validate_inputs()
            self.start_proxy(*params)  # 执行启动代理操作

        # 更新按钮状态
        self.proxy_running = not self.proxy_running
        self.btn.config(
            text="启动代理" if not self.proxy_running else "停止代理",
            command=self.toggle_proxy
        )

    # def start_proxy(self,a,b,c):
    #     """启动代理具体实现"""
    #     # 此处添加启动代理的代码（如调用系统命令）
    #     print("代理已启动")
    #     self.log.insert(tk.END, f"代理已启动\n")

    def start_proxy(self, remote_ip, remote_port, local_port):
        print("代理尝试启动")
        try:
            cmd = [
                "proxy.exe",
                remote_ip,
                str(remote_port),
                str(local_port)
            ]

            self.proxy_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            #self.proxy_running = True
            # self.control_btn.config(text="停止代理")
            self.log.insert(tk.END, f"代理已启动：{cmd}\n")

            # 启动线程监听输出
            threading.Thread(target=self.read_output, daemon=True).start()

        except Exception as e:
            messagebox.showerror("启动失败", str(e))
            #self.proxy_running = False

    # def stop_proxy(self):
    #     """停止代理具体实现"""
    #     # 此处添加停止代理的代码（如终止进程）
    #     print("代理已停止")

    def stop_proxy(self):
        print("代理尝试停止")
        if self.proxy_process:
            # 终止进程树
            kill_proc_tree(self.proxy_process.pid)
            self.proxy_process = None
            # 更新状态
            #self.proxy_running = False
            self.log.insert(tk.END, "代理已停止\n")

    def on_window_close(self):
        """ 窗口关闭事件处理函数 """
        if self.proxy_process:  # 终止代理进程
            kill_proc_tree(self.proxy_process.pid)
        self.root.destroy()  # 必须调用destroy彻底关闭

        #清理托盘图标
        if os.path.exists("temp_icon.ico"):
            os.remove("temp_icon.ico")


    ##################后台托盘图标管理##############################
    def load_tray_icon(self):
        """加载托盘图标资源"""
        # 生成临时图标文件（或准备本地图标文件）
        icon_path = self.generate_icon()
        self.tray_image = Image.open(icon_path)

        # 创建托盘菜单
        menu = (
            pystray.MenuItem("显示主界面", self.restore_window),
            pystray.MenuItem("退出", self.on_window_close)
        )

        # 初始化托盘图标
        self.tray_icon = pystray.Icon(
            "proxy_tool",
            icon=self.tray_image,
            menu=menu,
            title="TCP端口映射工具"
        )

    def generate_icon(self):
        """生成临时图标文件（可根据需要替换为自定义图标）"""
        from PIL import ImageDraw
        # 创建一个简单的默认图标
        image = Image.new('RGB', (64, 64), color=(73, 109, 137))
        draw = ImageDraw.Draw(image)
        draw.text((10, 10), "Proxy", fill=(255, 255, 255))
        temp_path = "temp_icon.ico"
        image.save(temp_path)
        return temp_path

    def minimize_to_tray(self):
        """最小化到托盘"""
        self.root.withdraw()  # 隐藏主窗口
        if not self.tray_icon_active:
            # 启动托盘图标线程
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            self.tray_icon_active = True

    def restore_window(self, icon=None, item=None):
        """从托盘恢复窗口"""
        self.root.deiconify()  # 显示主窗口
        self.root.lift()  # 置顶窗口



if __name__ == "__main__":
    app = ProxyController()
    app.root.mainloop()

