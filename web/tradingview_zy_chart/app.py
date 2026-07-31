import asyncio
import pathlib
import sys

# 将项目中的 src 目录，添加到 sys.path 中
src_path = pathlib.Path(__file__).parent.parent / ".." / "src"
sys.path.append(str(src_path))
web_server_path = pathlib.Path(__file__).parent
sys.path.append(str(web_server_path))


is_wpf_launcher = False
try:
    # WPF 启动，每次 print 都 flush，并且将字符编码转为 GBK（避免乱码）
    if "wpf_launcher" in sys.argv:
        is_wpf_launcher = True

        class filter:
            def __init__(self, target):
                self.target = target

            def write(self, s):
                self.target.buffer.write(s.encode("gbk"))
                self.target.flush()

            def flush(self):
                self.target.flush()

            def close(self):
                self.target.close()

        sys.stdin = filter(sys.stdin)
        sys.stdout = filter(sys.stdout)
        sys.stderr = filter(sys.stderr)

except Exception:
    pass

import traceback
import webbrowser
from concurrent.futures import ThreadPoolExecutor

from tornado.httpserver import HTTPServer
from tornado.wsgi import WSGIContainer

import tradingview_zy.encodefix  # Fix Windows print 乱码问题  # noqa: F401
from tradingview_zy import config

try:
    from cl_app import create_app
except Exception as e:
    print(e)
    traceback.print_exc()

    if is_wpf_launcher is False:
        input("出现异常，按回车键退出")


async def serve_forever() -> None:
    """Start the WSGI server inside an explicitly running asyncio loop."""
    app = create_app()
    executor = ThreadPoolExecutor(10)
    server = None

    try:
        server = HTTPServer(WSGIContainer(app, executor=executor))
        server.bind(9900, config.WEB_HOST)

        print("启动成功")
        server.start(1)

        if len(sys.argv) < 2 or sys.argv[1] != "nobrowser":
            webbrowser.open("http://127.0.0.1:9900")

        await asyncio.Event().wait()
    finally:
        if server is not None:
            server.stop()
            await server.close_all_connections()
        executor.shutdown(wait=False, cancel_futures=True)


def main() -> None:
    try:
        asyncio.run(serve_forever())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
        traceback.print_exc()

        if is_wpf_launcher is False:
            input("出现异常，按回车键退出")


if __name__ == "__main__":
    main()
