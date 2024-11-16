import ssl

def wrap_server_ssl(sock):
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
    return context.wrap_socket(sock, server_side=True)

def wrap_client_ssl(sock):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.load_verify_locations("cert.pem")
    return context.wrap_socket(sock, server_hostname="server")