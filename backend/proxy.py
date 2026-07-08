import socket
import subprocess
import threading
import sys
import os

def handle(client):
    print("New connection!")
    p = subprocess.Popen(['wsl', '-u', 'root', 'stdbuf', '-o0', '-i0', 'nc', '127.0.0.1', '5433'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    
    def r():
        while True:
            try:
                d = os.read(p.stdout.fileno(), 4096)
                if not d: break
                client.sendall(d)
            except Exception as e:
                print("Read error:", e)
                break
    
    threading.Thread(target=r, daemon=True).start()
    
    while True:
        try:
            d = client.recv(4096)
            if not d: break
            p.stdin.write(d)
            p.stdin.flush()
        except Exception as e:
            print("Write error:", e)
            break

s = socket.socket()
s.bind(('127.0.0.1', 5432))
s.listen(5)
print("Listening on 127.0.0.1:5432")

while True:
    c, addr = s.accept()
    threading.Thread(target=handle, args=(c,), daemon=True).start()
