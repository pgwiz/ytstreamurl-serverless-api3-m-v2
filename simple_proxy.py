import socket
import select
import threading
import sys

# Configuration
BIND_HOST = '::'  # Bind to all interfaces (IPv4 + IPv6 dual-stack)
BIND_PORT = 2082
BUFFER_SIZE = 8192

class ProxyServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        # Use IPv6 socket with dual-stack (also accepts IPv4)
        self.server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Allow IPv4 connections on this IPv6 socket
        self.server_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(100)
            print(f"[*] Proxy Server started on {self.host}:{self.port}")
            print(f"[*] Use this IP/Domain in your Vercel PROXY env var: http://<YOUR_SERVER_IP>:{self.port}")
            
            while True:
                client_socket, addr = self.server_socket.accept()
                # print(f"[*] Accepted connection from {addr[0]}:{addr[1]}")
                client_handler = threading.Thread(target=self.handle_client, args=(client_socket,))
                client_handler.daemon = True
                client_handler.start()
        except Exception as e:
            print(f"[!] Error: {e}")
        finally:
            self.server_socket.close()

    def handle_client(self, client_socket):
        try:
            request = client_socket.recv(BUFFER_SIZE)
            if not request:
                client_socket.close()
                return

            first_line = request.split(b'\n')[0]
            
            # --- Health Check Endpoint ---
            if b'GET /health' in first_line or b'GET / HTTP' in first_line:
                host_header = b''
                for line in request.split(b'\n'):
                    if line.lower().startswith(b'host:'):
                        # Get everything after "Host: " (handle Host: localhost:6178)
                        host_header = line.split(b':', 1)[1].strip().lower()
                        break
                # If the Host header points to our proxy (localhost, 127.x, :6178, or known domains)
                # Add your proxy domain here for direct response
                is_local = b'localhost' in host_header or b'127.' in host_header or b':2082' in host_header
                is_proxy_domain = b'servx.pgwiz.us.kg' in host_header or b'pgwiz' in host_header
                
                if is_local or is_proxy_domain:
                    response = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nProxy Server is Alive"
                    client_socket.send(response)
                    client_socket.close()
                    return
            
            url = first_line.split(b' ')[1]
            http_pos = url.find(b'://')
            
            if http_pos == -1:
                temp = url
            else:
                temp = url[(http_pos + 3):]

            port_pos = temp.find(b':')
            webserver_pos = temp.find(b'/')
            
            if webserver_pos == -1:
                webserver_pos = len(temp)

            webserver = ""
            port = -1

            if port_pos == -1 or webserver_pos < port_pos:
                port = 80
                webserver = temp[:webserver_pos]
            else:
                port = int((temp[(port_pos + 1):])[:webserver_pos - port_pos - 1])
                webserver = temp[:port_pos]

            if b'CONNECT' in first_line:
                self.handle_https_tunnel(client_socket, webserver, port)
            else:
                self.handle_http_request(client_socket, request, webserver, port)

        except Exception as e:
            # print(f"[!] Processing error: {e}")
            client_socket.close()

    def handle_https_tunnel(self, client_socket, host, port):
        try:
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((host, port))
            client_socket.send(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            
            self.forward_data(client_socket, remote_socket)
        except Exception as e:
            # print(f"[!] HTTPS Tunnel Error: {e}")
            client_socket.close()

    def handle_http_request(self, client_socket, request, host, port):
        try:
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((host, port))
            remote_socket.send(request)
            
            self.forward_data(client_socket, remote_socket)
        except Exception as e:
            # print(f"[!] HTTP Request Error: {e}")
            client_socket.close()
            if 'remote_socket' in locals():
                remote_socket.close()

    def forward_data(self, client, remote):
        try:
            sockets = [client, remote]
            while True:
                readable, _, _ = select.select(sockets, [], [], 60)
                if not readable:
                    break
                
                for sock in readable:
                    other = remote if sock is client else client
                    data = sock.recv(BUFFER_SIZE)
                    if not data:
                        return
                    other.send(data)
        except:
            pass
        finally:
            client.close()
            remote.close()

if __name__ == '__main__':
    proxy = ProxyServer(BIND_HOST, BIND_PORT)
    proxy.start()
