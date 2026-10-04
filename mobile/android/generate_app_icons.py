import os
from PIL import Image, ImageDraw

SOURCE_ICON = "store_assets/app_icon_512x512.png"
RES_DIR = "mobile/android/app/src/main/res"
BG_COLOR = (8, 4, 32, 255) # Hex #080420

def generate():
    if not os.path.exists(SOURCE_ICON):
        raise FileNotFoundError(f"Source icon not found at {SOURCE_ICON}")

    src = Image.open(SOURCE_ICON).convert("RGBA")

    # Dimensions for standard launcher icons
    mipmap_sizes = {
        "mipmap-mdpi": (48, 108),
        "mipmap-hdpi": (72, 162),
        "mipmap-xhdpi": (96, 216),
        "mipmap-xxhdpi": (144, 324),
        "mipmap-xxxhdpi": (192, 432),
    }

    print("Generating Android mipmap icons...")
    for folder, (legacy_size, fg_size) in mipmap_sizes.items():
        folder_path = os.path.join(RES_DIR, folder)
        os.makedirs(folder_path, exist_ok=True)

        # 1. ic_launcher.png (legacy square/rounded)
        legacy_icon = src.resize((legacy_size, legacy_size), Image.Resampling.LANCZOS)
        legacy_path = os.path.join(folder_path, "ic_launcher.png")
        legacy_icon.save(legacy_path, "PNG")
        print(f"  Saved {legacy_path} ({legacy_size}x{legacy_size})")

        # 2. ic_launcher_round.png (circular mask)
        round_icon = src.resize((legacy_size, legacy_size), Image.Resampling.LANCZOS)
        mask = Image.new("L", (legacy_size, legacy_size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, legacy_size, legacy_size), fill=255)
        round_icon.putalpha(mask)
        round_path = os.path.join(folder_path, "ic_launcher_round.png")
        round_icon.save(round_path, "PNG")
        print(f"  Saved {round_path} ({legacy_size}x{legacy_size})")

        # 3. ic_launcher_foreground.png (adaptive foreground, 108dp canvas, ~72% safe zone)
        fg_canvas = Image.new("RGBA", (fg_size, fg_size), BG_COLOR)
        logo_size = int(fg_size * 0.72)
        logo_scaled = src.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        pos = ((fg_size - logo_size) // 2, (fg_size - logo_size) // 2)
        fg_canvas.paste(logo_scaled, pos, logo_scaled)
        fg_path = os.path.join(folder_path, "ic_launcher_foreground.png")
        fg_canvas.save(fg_path, "PNG")
        print(f"  Saved {fg_path} ({fg_size}x{fg_size})")

    # Update ic_launcher_background.xml
    bg_xml_path = os.path.join(RES_DIR, "values", "ic_launcher_background.xml")
    with open(bg_xml_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">#080420</color>\n</resources>\n')
    print(f"Updated {bg_xml_path} background color to #080420")

    # Remove obsolete vector files if they exist
    obsolete_files = [
        os.path.join(RES_DIR, "drawable-v24", "ic_launcher_foreground.xml"),
        os.path.join(RES_DIR, "drawable", "ic_launcher_background.xml"),
    ]
    for obs in obsolete_files:
        if os.path.exists(obs):
            os.remove(obs)
            print(f"Removed obsolete vector {obs}")

    # Update splash images
    print("Updating splash screens...")
    for root, dirs, files in os.walk(RES_DIR):
        for file in files:
            if file == "splash.png":
                splash_path = os.path.join(root, file)
                try:
                    with Image.open(splash_path) as current_splash:
                        w, h = current_splash.size
                    
                    new_splash = Image.new("RGB", (w, h), (8, 4, 32))
                    # Scale logo so it is nicely centered (~30% of smallest dimension)
                    min_dim = min(w, h)
                    splash_logo_size = int(min_dim * 0.35)
                    scaled_splash_logo = src.resize((splash_logo_size, splash_logo_size), Image.Resampling.LANCZOS)
                    pos = ((w - splash_logo_size) // 2, (h - splash_logo_size) // 2)
                    new_splash.paste(scaled_splash_logo, pos, scaled_splash_logo)
                    new_splash.save(splash_path, "PNG")
                    print(f"  Updated splash: {splash_path} ({w}x{h})")
                except Exception as e:
                    print(f"  Could not update {splash_path}: {e}")

    # Copy to mobile/public for web PWA / browser
    os.makedirs("mobile/public", exist_ok=True)
    src.resize((64, 64), Image.Resampling.LANCZOS).save("mobile/public/favicon.png", "PNG")
    src.resize((192, 192), Image.Resampling.LANCZOS).save("mobile/public/icon.png", "PNG")
    print("Saved public web icons in mobile/public/")

if __name__ == "__main__":
    generate()
