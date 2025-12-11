from multiprocessing.dummy import Pool as ThreadPool
import time
def check_host_status(host):
    """Kiểm tra trạng thái hoạt động của một danh sách máy chủ"""
    time.sleep(2)  # Giả lập độ trễ khi kiểm tra
    print(f"Đang kiểm tra: {host} - Hoạt động ổn định")
hosts = ["server1.vietnix.vn", "server2.vietnix.vn", "server3.vietnix.vn"]
pool = ThreadPool(3)
pool.map(check_host_status, hosts)
pool.close()
pool.join()