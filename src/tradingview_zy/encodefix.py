import sys


class filter:
    def __init__(self, target):
        self.target = target

    def write(self, s):
        self.target.buffer.write(s.encode("utf-8"))

    def flush(self):
        self.target.flush()

    def close(self):
        self.target.close()


if sys.platform == "win32":
    # 只包装输出流。stdin 包装后没有 readline，会让 input() 抛
    # AttributeError，异常兜底的“按回车键退出”反而把真正的报错顶掉。
    sys.stdout = filter(sys.stdout)
    sys.stderr = filter(sys.stderr)
