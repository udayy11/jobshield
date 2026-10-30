import os
from PIL import Image, ImageDraw

def create_shield_icon(size, filename):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    pad = int(size * 0.1)
    w = size - 2 * pad
    h = size - 2 * pad
    
    # Shield points
    x0, y0 = pad, pad
    x1, y1 = size - pad, size - pad
    xm, ym = size // 2, pad + int(h * 0.6)
    
    # Shield polygon
    points = [
        (xm, y0),
        (x1, y0 + int(h * 0.2)),
        (x1, y0 + int(h * 0.6)),
        (xm, y1),
        (x0, y0 + int(h * 0.6)),
        (x0, y0 + int(h * 0.2)),
    ]
    
    # Gradient/Color: Vibrant Cyan-Blue with Navy background
    draw.polygon(points, fill=(14, 165, 233, 255), outline=(56, 189, 248, 255), width=max(1, size // 24))
    
    # Inner checkmark or key symbol
    cx = size // 2
    cy = size // 2
    r = max(2, size // 6)
    draw.ellipse([cx - r, cy - r - 2, cx + r, cy + r - 2], fill=(255, 255, 255, 240))
    draw.rectangle([cx - max(1, r // 3), cy - 2, cx + max(1, r // 3), cy + r + 4], fill=(255, 255, 255, 240))
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    img.save(filename, "PNG")
    print(f"Generated icon: {filename} ({size}x{size})")

if __name__ == "__main__":
    create_shield_icon(16, "extension/icon16.png")
    create_shield_icon(48, "extension/icon48.png")
    create_shield_icon(128, "extension/icon128.png")
