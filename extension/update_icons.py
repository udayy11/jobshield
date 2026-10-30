"""
JobShield AI — Icon Synchronization Utility
Automatically extracts icon sizes (16x16, 48x48, 128x128) from favicon.ico to update Chrome extension icons.
"""

import os
from PIL import Image

def update_extension_icons():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(base_dir, "favicon.ico")

    if not os.path.exists(ico_path):
        print(f"[-] favicon.ico not found at {ico_path}. Please place your .ico file there.")
        return

    try:
        with Image.open(ico_path) as img:
            sizes = [(16, "icon16.png"), (48, "icon48.png"), (128, "icon128.png")]
            for size, filename in sizes:
                target_path = os.path.join(base_dir, filename)
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                resized.save(target_path, "PNG")
                print(f"[PASS] Generated {filename} ({size}x{size})")
        print("[SUCCESS] All Chrome extension icons updated successfully from favicon.ico!")
    except Exception as e:
        print(f"[-] Error processing favicon.ico: {e}")

if __name__ == "__main__":
    update_extension_icons()
