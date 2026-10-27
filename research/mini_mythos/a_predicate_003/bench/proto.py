"""Message channel between the observer and bench nodes: AF_UNIX SOCK_SEQPACKET, one JSON object per message,
optional SCM_RIGHTS file descriptors (socket.send_fds / recv_fds).  WRITTEN, NOT RUN."""
import json
import socket

import common as C

MAX_MSG = 1 << 16
MAX_FDS = 4


class ProtoError(RuntimeError):
    pass


class ProtoTimeout(ProtoError):
    pass


class ProtoEOF(ProtoError):
    pass


def socketpair():
    return socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)


def send_msg(sock, obj, fds=()):
    data = json.dumps(obj, separators=(",", ":"), default=str).encode("utf-8")
    if len(data) > MAX_MSG:
        raise ProtoError("message too large: %d" % len(data))
    sock.settimeout(10.0)
    if fds:
        socket.send_fds(sock, [data], list(fds))
    else:
        sock.send(data)


def recv_msg(sock, timeout):
    """-> (obj, fds).  Raises ProtoTimeout / ProtoEOF.  A truncated datagram is a protocol error (received fds are closed)."""
    import os
    sock.settimeout(timeout)
    try:
        data, fds, flags, _addr = socket.recv_fds(sock, MAX_MSG, MAX_FDS)
    except socket.timeout:
        raise ProtoTimeout("recv timeout")
    except (ConnectionResetError, BrokenPipeError):
        raise ProtoEOF("connection reset")
    if flags & socket.MSG_TRUNC or flags & socket.MSG_CTRUNC:
        for fd in fds:
            os.close(fd)
        raise ProtoError("truncated message")
    if not data and not fds:
        raise ProtoEOF("eof")
    try:
        return json.loads(data.decode("utf-8")), list(fds)
    except ValueError:
        for fd in fds:
            os.close(fd)
        raise ProtoError("undecodable message")


class Channel:
    """A socket plus an inbox for messages that arrived while waiting for a different type."""

    def __init__(self, sock):
        self.sock = sock
        self.inbox = []
        self.eof = False

    def send(self, obj, fds=()):
        send_msg(self.sock, obj, fds)

    def recv(self, timeout):
        if self.inbox:
            return self.inbox.pop(0)
        return recv_msg(self.sock, timeout)

    def expect(self, types, timeout):
        """First message whose 't' is in types (earlier non-matching messages stay queued, in order)."""
        for i, (m, f) in enumerate(self.inbox):
            if m.get("t") in types:
                return self.inbox.pop(i)
        deadline = C.mono() + timeout
        while True:
            left = deadline - C.mono()
            if left <= 0:
                raise ProtoTimeout("expect %r" % (sorted(types),))
            m, f = recv_msg(self.sock, left)
            if m.get("t") in types:
                return m, f
            self.inbox.append((m, f))

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass
