from PIL import Image, ImageDraw
import os
import random

def create_icon(size, output_path):
    """Create a simple icon with satellite design"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw background circle
    center = size // 2
    radius = size // 2 - 10
    
    # Gradient-like effect
    for i in range(radius, 0, -1):
        alpha = int(255 * (i/radius))
        color = (62, 207, 142, alpha)
        draw.ellipse([center-i, center-i, center+i, center+i], 
                    fill=color, outline=None)
    
    # Draw satellite dish
    draw.ellipse([center-30, center-30, center+30, center+30], 
                 outline='white', width=3)
    
    # Draw satellite body
    draw.rectangle([center-15, center-50, center+15, center-30], 
                   fill='white')
    
    # Add stars
    for _ in range(5):
        x = center + random.randint(-40, 40)
        y = center + random.randint(-40, 40)
        draw.ellipse([x-2, y-2, x+2, y+2], fill='white')
    
    img.save(output_path)
    print(f"Created {output_path}")

# Create directories
os.makedirs('static/icons', exist_ok=True)
os.makedirs('static/splash', exist_ok=True)

# Create manifest.json
manifest_content = '''{
  "name": "Starlink Kenya",
  "short_name": "Starlink",
  "description": "High-Speed Satellite Internet Payments - Powered by SpaceX",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0a0e17",
  "theme_color": "#3ecf8e",
  "orientation": "portrait",
  "scope": "/",
  "categories": ["business", "finance", "utilities"],
  "icons": [
    {
      "src": "/static/icons/icon-72x72.png",
      "sizes": "72x72",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-96x96.png",
      "sizes": "96x96",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-128x128.png",
      "sizes": "128x128",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-144x144.png",
      "sizes": "144x144",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-152x152.png",
      "sizes": "152x152",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-384x384.png",
      "sizes": "384x384",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ]
}'''

with open('static/manifest.json', 'w') as f:
    f.write(manifest_content)

print("✅ Created manifest.json")

# Generate icons
sizes = [72, 96, 128, 144, 152, 192, 384, 512]
for size in sizes:
    create_icon(size, f'static/icons/icon-{size}x{size}.png')

print("✅ All files created successfully!")