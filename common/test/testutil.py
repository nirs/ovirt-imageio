# ovirt-imageio-common
# Copyright (C) 2015-2016 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import absolute_import

import collections
import errno
import logging
import socket
import time

from contextlib import closing

log = logging.getLogger("test")


def fill(b, size):
    count, rest = divmod(size, len(b))
    return b * count + b[:rest]


BUFFER = fill(b"ABCDEFGHIJ", 1024**2)
BLOCK = fill(b"abcdefghij", 512)
BYTES = fill(b"0123456789", 42)


def head(b):
    return b[:10]


class UnbufferedStream(object):
    """
    Unlike regular file object, read may return any amount of bytes up to the
    requested size. This behavior is probably the result of doing one syscall
    per read, without any buffering.

    This stream will break code assuming that read(n) retruns n bytes. This
    assumption is normally true, but not all file-like objects behave in this
    way.

    This simulate libvirt stream behavior used to copy imaged directly from
    libvirt.
    https://libvirt.org/html/libvirt-libvirt-stream.html#virStreamRecv
    """

    def __init__(self, chunks):
        self.chunks = collections.deque(chunks)

    def read(self, size):
        if not self.chunks:
            return b''
        chunk = self.chunks.popleft()
        res = chunk[:size]
        chunk = chunk[size:]
        if chunk:
            self.chunks.appendleft(chunk)
        return res


def wait_for_socket(addr, timeout, step=0.02):
    start = time.time()
    elapsed = 0.0

    if addr.transport == "unix":
        sock = socket.socket(socket.AF_UNIX)
    elif addr.transport == "tcp":
        # TODO: IPV6 support.
        sock = socket.socket(socket.AF_INET)
    else:
        raise RuntimeError("Cannot wait for {}".format(addr))

    with closing(sock):
        while elapsed < timeout:
            try:
                sock.connect(addr)
            except socket.error as e:
                if e.args[0] not in (errno.ECONNREFUSED, errno.ENOENT):
                    raise
                time.sleep(step)
                elapsed = time.time() - start
            else:
                log.debug("Waited for %s %.3f seconds", addr, elapsed)
                return True

        return False
