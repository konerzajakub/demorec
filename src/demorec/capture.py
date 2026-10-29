"""Screencast reader, run as its own process by Cast.

A thread in the scene's process shares the interpreter lock with the scene, and busy scene code
held back the acks, so Chrome painted fewer frames. A process acks every frame at once.

    python -m demorec.capture <port> <target_id> <dir> <prefix> <max_width> <max_height>

Writes <dir>/<prefix>NNNNNN.jpg and one line per frame to <dir>/<prefix>index.tsv:
browser timestamp, wall clock at arrival, width, height, file name. Stops when stdin closes."""
import base64, os, sys, threading, time

from .cdp import CDP


def jpeg_size(b):
    """(width, height) from the JPEG frame header."""
    i = 2
    while i + 9 < len(b):
        marker, n = b[i + 1], int.from_bytes(b[i + 2:i + 4], "big")
        if marker in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(b[i + 7:i + 9], "big"), int.from_bytes(b[i + 5:i + 7], "big")
        i += 2 + n
    return 0, 0


def stop_on_eof(cdp):
    """Cast closes our stdin to end the capture."""
    sys.stdin.read()
    try: cdp.send("Page.stopScreencast")
    except OSError: pass
    cdp.close()


def screencast_frames(cdp):
    """Yields (frame event params, wall clock at arrival). Each frame is acked before anything
    else happens to it, so Chrome sends the next one right away."""
    while True:
        msg = cdp.recv()
        if msg.get("method") != "Page.screencastFrame":
            continue
        e = msg["params"]
        cdp.send("Page.screencastFrameAck", {"sessionId": e["sessionId"]})
        yield e, time.time()


def main(port, target, out, prefix, max_w, max_h):
    cdp = CDP(int(port), target)
    threading.Thread(target=stop_on_eof, args=(cdp,), daemon=True).start()
    cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 93, "maxWidth": int(max_w),
                                      "maxHeight": int(max_h), "everyNthFrame": 1})
    with open(os.path.join(out, prefix + "index.tsv"), "w", encoding="utf-8") as idx:
        try:
            for n, (e, wall) in enumerate(screencast_frames(cdp)):
                b = base64.b64decode(e["data"])
                name = "%s%06d.jpg" % (prefix, n)
                with open(os.path.join(out, name), "wb") as f:
                    f.write(b)
                w, h = jpeg_size(b)
                idx.write("%.6f\t%.6f\t%d\t%d\t%s\n" % (e["metadata"]["timestamp"], wall, w, h, name))
        except (ConnectionError, OSError):
            pass  # the page closed or stop_on_eof() closed the connection


if __name__ == "__main__":
    main(*sys.argv[1:7])
