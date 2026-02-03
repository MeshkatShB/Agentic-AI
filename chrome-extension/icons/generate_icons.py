#!/usr/bin/env python3
"""
Generate icon files for Chrome extension.
Creates icon16.png, icon48.png, and icon128.png
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    import os
except ImportError:
    print("PIL (Pillow) is required. Install it with: pip install Pillow")
    exit(1)

def create_icon(size, output_path):
    """Create an icon with the specified size."""
    # Create a new image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Define colors (purple gradient matching the extension theme)
    primary_color = (139, 92, 246)  # #8b5cf6
    secondary_color = (124, 58, 237)  # #7c3aed
    accent_color = (255, 255, 255)  # White
    
    # Draw a rounded rectangle background with gradient effect
    margin = size // 8
    corner_radius = size // 6
    
    # Create gradient effect by drawing multiple rectangles
    for i in range(margin, size - margin):
        # Interpolate color
        ratio = (i - margin) / (size - 2 * margin)
        r = int(primary_color[0] * (1 - ratio) + secondary_color[0] * ratio)
        g = int(primary_color[1] * (1 - ratio) + secondary_color[1] * ratio)
        b = int(primary_color[2] * (1 - ratio) + secondary_color[2] * ratio)
        draw.rectangle(
            [(margin, i), (size - margin, i + 1)],
            fill=(r, g, b, 255)
        )
    
    # Draw a simple "AI" symbol - brain/neural network style
    center = size // 2
    
    # Draw a stylized "A" shape using lines
    if size >= 48:
        # For larger icons, draw a more detailed "A"
        line_width = max(2, size // 16)
        # Draw triangle shape (A)
        points = [
            (center, size // 4),  # Top
            (center - size // 4, size * 3 // 4),  # Bottom left
            (center + size // 4, size * 3 // 4),  # Bottom right
        ]
        draw.polygon(points, fill=accent_color, outline=accent_color)
        # Draw horizontal line
        draw.line(
            [(center - size // 6, center), (center + size // 6, center)],
            fill=(0, 0, 0, 255),  # Black line
            width=line_width
        )
    else:
        # For small icons, draw a simple circle with dot
        radius = size // 4
        draw.ellipse(
            [center - radius, center - radius, center + radius, center + radius],
            fill=accent_color,
            outline=accent_color
        )
        # Add a small dot in center
        dot_radius = size // 8
        draw.ellipse(
            [center - dot_radius, center - dot_radius, center + dot_radius, center + dot_radius],
            fill=(0, 0, 0, 255)
        )
    
    # Save the image
    img.save(output_path, 'PNG')
    print(f"Created {output_path} ({size}x{size})")

def main():
    """Generate all icon files."""
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create icons
    sizes = [16, 48, 128]
    for size in sizes:
        output_path = os.path.join(script_dir, f"icon{size}.png")
        create_icon(size, output_path)
    
    print("\nAll icon files created successfully!")
    print("Files created:")
    for size in sizes:
        print(f"  - icon{size}.png")

if __name__ == "__main__":
    main()

