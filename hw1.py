# Allowed Modules
import logging
import socket
import sys
import gzip 
import ssl
# End of Allowed Modules
# Adding any extra module will result into score of 0


def parse_url(url: str):
    # break the url into scheme host port and path
    # if anything weird just return none

    url = url.strip()

    # check scheme
    if url.startswith("http://"):
        scheme = "http"
        rest = url[7:]
        port = 80
    elif url.startswith("https://"):
        scheme = "https"
        rest = url[8:]
        port = 443
    else:
        return None

    # find first slash
    slash_index = rest.find("/")
    if slash_index == -1:
        authority = rest
        path = "/"
    else:
        authority = rest[:slash_index]
        path = rest[slash_index:]
        if path == "":
            path = "/"

    if authority == "":
        return None

    host = authority

    # basic host:port support
    if ":" in authority:
        parts = authority.rsplit(":", 1)
        if len(parts) != 2:
            return None
        host = parts[0]
        port_str = parts[1]

        if not port_str.isdigit():
            return None

        port = int(port_str)

    return scheme, host, port, path


def parse_response_headers(header_bytes: bytes):
    # take raw header bytes and turn into status code and dict

    lines = header_bytes.split(b"\r\n")

    if len(lines) == 0:
        return None, {}

    # first line should be status
    first_line = lines[0].decode("iso-8859-1", "replace")
    pieces = first_line.split(" ")

    if len(pieces) < 2:
        return None, {}

    try:
        status_code = int(pieces[1])
    except:
        return None, {}

    headers = {}

    # go through remaining lines
    for i in range(1, len(lines)):
        line = lines[i]
        if line == b"":
            continue

        if b":" not in line:
            continue

        split_line = line.split(b":", 1)
        name = split_line[0]
        value = split_line[1]

        header_name = name.decode("iso-8859-1", "replace").strip().lower()
        header_value = value.decode("iso-8859-1", "replace").strip()

        headers[header_name] = header_value

    return status_code, headers


def decode_chunked_body(body: bytes):
    # very basic chunked decoder
    # read size line then read that many bytes

    index = 0
    result = bytearray()

    while True:
        # find end of size line
        line_end = body.find(b"\r\n", index)
        if line_end == -1:
            return None

        size_bytes = body[index:line_end]
        index = line_end + 2

        size_bytes = size_bytes.strip()
        if size_bytes == b"":
            return None

        try:
            chunk_size = int(size_bytes.decode("ascii"), 16)
        except:
            return None

        # size 0 means done
        if chunk_size == 0:
            return bytes(result)

        if index + chunk_size > len(body):
            return None

        # add chunk data
        for j in range(chunk_size):
            result.append(body[index + j])

        index += chunk_size

        # skip trailing \r\n
        if body[index:index+2] != b"\r\n":
            return None

        index += 2


def retrieve_url(url: str):
    # main function
    # try up to 10 redirects

    redirect_count = 0

    while redirect_count <= 10:

        parsed = parse_url(url)
        if parsed is None:
            return None

        scheme = parsed[0]
        host = parsed[1]
        port = parsed[2]
        path = parsed[3]

        sock = None

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))

            if scheme == "https":
                context = ssl.create_default_context()
                sock = context.wrap_socket(sock, server_hostname=host)

            # build request manually
            request = ""
            request += "GET " + path + " HTTP/1.1\r\n"
            request += "Host: " + host + "\r\n"
            request += "Connection: close\r\n"
            request += "User-Agent: hw1-client\r\n"
            request += "\r\n"

            sock.sendall(request.encode("ascii"))

            # read everything
            response_bytes = bytearray()

            while True:
                data = sock.recv(4096)
                if not data:
                    break
                response_bytes.extend(data)

        except:
            return None
        finally:
            if sock is not None:
                try:
                    sock.close()
                except:
                    pass

        response = bytes(response_bytes)

        header_end = response.find(b"\r\n\r\n")
        if header_end == -1:
            return None

        header_bytes = response[:header_end]
        body = response[header_end + 4:]

        status_code, headers = parse_response_headers(header_bytes)

        if status_code is None:
            return None

        # handle redirects
        if 300 <= status_code <= 399:
            location = headers.get("location")
            if location is None:
                return None

            if location.startswith("http://") or location.startswith("https://"):
                url = location
            elif location.startswith("/"):
                url = scheme + "://" + host + location
            else:
                return None

            redirect_count += 1
            continue

        # only return for 200
        if status_code != 200:
            return None

        # check chunked
        transfer = headers.get("transfer-encoding", "")
        if "chunked" in transfer.lower():
            decoded = decode_chunked_body(body)
            if decoded is None:
                return None
            body = decoded

        return body

    return None


if __name__ == "__main__":
    sys.stdout.buffer.write(retrieve_url(sys.argv[1]))
