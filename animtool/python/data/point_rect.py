
class PointRect:
    def __init__(self, x=0, y=0, w=0, h=0):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def __str__(self):
        return f"[{self.x},{self.y},{self.w},{self.h}]"
