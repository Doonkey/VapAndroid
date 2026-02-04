from data.point_rect import PointRect
from PIL import Image
import numpy as np

class GetAlphaFrame:
    
    class AlphaFrameOut:
        def __init__(self, argb=None):
            # We assume argb in Python will be a PILLOW IMAGE object for efficiency
            # instead of a massive int array.
            self.image = argb # PIL Image

    def create_frame(self, common_arg, input_file):
        if not input_file or not input_file.exists():
            return None
            
        w = common_arg.rgb_point.w
        h = common_arg.rgb_point.h
        out_w = common_arg.output_w
        out_h = common_arg.output_h
        
        try:
            input_buf = Image.open(input_file).convert("RGBA")
        except Exception:
            return None
            
        # Create output image (canvas)
        # Background strictly 0x00000000 ? Java fills with 0xff000000 (Opaque Black)
        # "Arrays.fill(outputArgb, 0xff000000);"
        # So background is Opaque Black.
        output_img = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 255))
        
        alpha_buf = input_buf
        
        if common_arg.scale < 1.0:
            new_w = int(w * common_arg.scale)
            new_h = int(h * common_arg.scale)
            alpha_buf = input_buf.resize((new_w, new_h), Image.BILINEAR)
            
        # Fill RGB area
        self.fill_color(output_img, common_arg.rgb_point, False, input_buf)
        
        # Fill Alpha area
        self.fill_color(output_img, common_arg.alpha_point, True, alpha_buf)
        
        return self.AlphaFrameOut(output_img)

    def fill_color(self, output_img, point, is_alpha, input_img):
        # Determine source matching region?
        # Java logic: iterates x,y from 0 to point.w/h.
        # inputArgb[x + y * inputW]. 
        # So it takes 0,0 from input.
        
        # Cropping input to point.w / point.h?
        # Implicitly, the input image is assumed to be at least point size.
        # If input_img is larger, we crop top-left.
        
        src_w, src_h = input_img.size
        # Clip breadth
        copy_w = min(point.w, src_w)
        copy_h = min(point.h, src_h)
        
        if copy_w <= 0 or copy_h <= 0:
            return

        source_region = input_img.crop((0, 0, copy_w, copy_h))
        
        if is_alpha:
            processed = self.process_alpha_region(source_region)
            output_img.paste(processed, (point.x, point.y))
        else:
            processed = self.process_color_region(source_region)
            output_img.paste(processed, (point.x, point.y))

    def process_color_region(self, img):
        # getColor(color) -> blendBg(color, 0xff000000)
        # It blends the pixel with Black background. 
        # r = alpha * colorR + (1-alpha)*0 
        # Basically premultiplied alpha on black?
        # But maintains Alpha=255 (Opaque) result.
        
        # Create a black background image
        bg = Image.new("RGBA", img.size, (0, 0, 0, 255))
        
        # Composite img over bg
        # Image.alpha_composite requires both RGBA
        # output = img OVER bg.
        comp = Image.alpha_composite(bg, img)
        
        # Result is RGBA. Java logic returns 0xff000000 + r + g + b. 
        # Meaning Alpha is forced to 255.
        # Check if alpha_composite does that. Yes, result is opaque if bg is opaque.
        return comp

    def process_alpha_region(self, img):
        # getAlpha(color):
        # alpha = color >>> 24
        # return 0xff..... + alpha<<16 + ...
        # Returns grayscale opaque pixel based on Alpha channel.
        
        # Extract alpha
        r, g, b, a = img.split()
        
        # Create new image where R=G=B=A_channel, A=255
        opaque = Image.new("L", img.size, 255)
        
        # Use 'a' as the grayscale value
        res = Image.merge("RGBA", (a, a, a, opaque))
        return res
