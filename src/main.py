import socket

port = 2605
host = "127.0.0.1"


def main() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", port))

    print(f"listening on port: {port}")
    server.listen(1)

    conn, _ = server.accept()
    with conn:
        data = conn.recv(4096)
        print(f"{data.decode()}")


if __name__ == "__main__":
    main()
