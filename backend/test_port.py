import socket

for ip in ['127.0.0.1', '172.21.128.63', 'localhost', '::1']:
    try:
        s = socket.socket(socket.AF_INET if ':' not in ip else socket.AF_INET6, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((ip, 5432))
        print(f"{ip} works")
        s.close()
    except Exception as e:
        print(f"{ip} failed: {e}")
