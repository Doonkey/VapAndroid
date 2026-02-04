
class TLog:
    logger = None

    @staticmethod
    def i(tag: str, msg: str):
        if TLog.logger:
            TLog.logger.i(tag, msg)
        else:
            print(f"{tag}\t{msg}")

    @staticmethod
    def e(tag: str, msg: str):
        if TLog.logger:
            TLog.logger.e(tag, msg)
        else:
            print(f"{tag}\tError:{msg}")

    @staticmethod
    def w(tag: str, msg: str):
        if TLog.logger:
            TLog.logger.w(tag, msg)
        else:
            print(f"{tag}\tWarning:{msg}")

class ITLog:
    def i(self, tag: str, msg: str): pass
    def e(self, tag: str, msg: str): pass
    def w(self, tag: str, msg: str): pass
