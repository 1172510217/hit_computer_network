import select
import socket
import threading


class Server:
    server_address = ('127.0.0.1', 12340)

    def __init__(self):
        super().__init__()
        self.window_size = 5  # 窗口尺寸
        self.send_base = 0  # 最小的被发送的分组序号
        self.next_seq = 0  # 当前未被利用的序号
        self.time_count = 0  # 记录当前传输时间
        self.time_out = 10  # 设置超时时间
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.server_address)  # 绑定套接字的本地IP地址和端口号
        self.data = []  # 缓存发送数据
        self.read_path = '../file/read_file.txt'  # 需要发送的源文件数据
        self.buf_size = 10
        self.get_data_from_file()

    def make_pkt(self, data):
        return (str(self.next_seq) + ' ' + str(data)).encode(encoding='utf-8')

    # 若仍剩余窗口空间，则构造数据报发送；否则拒绝发送数据
    def send_data(self):
        if self.next_seq < self.send_base + self.window_size:  # 窗口中仍有可用空间
            self.socket.sendto(self.make_pkt(self.data[self.next_seq]),
                               Client.client_address)
            if self.send_base == self.next_seq:
                self.time_count = 0
            self.next_seq += 1
            print('服务器:成功发送数据')
            return True
        else:  # 窗口中无可用空间
            print('服务器：窗口已满，暂不发送数据')
            return False

    # 超时处理函数：计时器置0
    def handle_time_out(self):
        print('超时，开始重传')
        self.time_count = 0
        for i in range(self.send_base,
                       self.next_seq if self.next_seq > self.send_base
                       else self.next_seq + self.window_size):
            self.socket.sendto(self.make_pkt(self.data[(self.send_base + i)]),
                               Client.client_address)
            print('数据已重发:' + str(self.send_base + i))

    # 处理收到的客户端ACK报文
    def rcv_pkt(self, data):
        rcv_num = int(data.decode().split()[0])
        self.send_base = (rcv_num + 1)  # 收到ACK，更新窗口起点
        self.time_count = 0  # 重置定时器

    def get_data_from_file(self):
        f = open(self.read_path, 'r', encoding='utf-8')
        while True:
            send_data = f.read(1024)
            if len(send_data) <= 0:
                break
            self.data.append(send_data)

    def run(self):
        while True:
            self.send_data()  # 发送数据逻辑
            readable = select.select([self.socket, ], [], [], 1)[0]
            if len(readable) > 0:
                rcv_ack = self.socket.recvfrom(self.buf_size)[0].decode()  # 接收ACK数据逻辑
                print('收到客户端ACK:' + rcv_ack)
                self.send_base = int(rcv_ack) + 1  # 滑动窗口的起始序号
            else:
                self.time_count += 1
                if self.time_count > self.time_out:
                    self.handle_time_out()
            if self.next_seq == len(self.data):
                print('服务器数据传输结束')
                break


class Client:
    client_address = ('127.0.0.1', 12341)

    def __init__(self):
        super().__init__()
        self.buf_size = 1678
        self.time_out = 3  # 超时时间
        self.time_count = 0  # 用于超时次数计数
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        self.socket.bind(Client.client_address)
        self.exp_seq = 0  # 当前期望收到该序号的数据
        self.save_path = '../file/config_file.txt'  # 保存数据的地址
        with open(self.save_path, 'w') as f:
            f.write('')

    def make_ack_pkt(self):
        return str(self.exp_seq - 1).encode()

    # 保存来自服务器的合适的数据
    def write_data_to_file(self, data):
        with open(self.save_path, mode='a', encoding='utf-8') as f:
            f.write(data)
        return

    # 主要执行函数，不断接收服务器发送的数据，若为期待序号的数据，则保存到本地，否则直接丢弃；并返回相应的ACK报文
    def run(self):
        while True:
            readable = select.select([self.socket, ], [], [], 1)[0]
            if len(readable) > 0:
                rcv_data = self.socket.recvfrom(self.buf_size)[0].decode()
                rcv_seq = rcv_data.split()[0]
                rcv_data = rcv_data.replace(rcv_seq + ' ', '')
                if int(rcv_seq) == self.exp_seq:
                    print('收到服务器发来的期望序号数据')
                    self.write_data_to_file(rcv_data)  # 保存服务器端发送的数据到本地文件中
                    self.exp_seq += 1  # 期望数据的序号更新
                else:
                    print('服务器数据非期望数据')
                self.socket.sendto(self.make_ack_pkt(), Server.server_address)
            else:
                self.time_count += 1
                if self.time_count >= self.time_out:
                    print('超时:传输结束')
                    break


if __name__ == '__main__':
    server = Server()
    client = Client()
    threading.Thread(target=server.run).start()  # 注意这里函数一定不能带括号
    threading.Thread(target=client.run).start()  # 注意这里函数一定不能带括号
