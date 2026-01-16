from PIL import Image, ImageDraw, ImageFont
import math

def draw_icon(size):
    """Рисует иконку с белым кругом, разноцветными треугольниками и буквами AI в центре"""
    # Создаем изображение с черным фоном
    img = Image.new("RGB", (size, size), (0, 0, 0))  # Черный фон
    draw = ImageDraw.Draw(img)
    
    center_x = size // 2
    center_y = size // 2
    
    # Радиус белого круга
    circle_radius = size * 0.35
    
    # Рисуем белый круг
    draw.ellipse([
        int(center_x - circle_radius),
        int(center_y - circle_radius),
        int(center_x + circle_radius),
        int(center_y + circle_radius)
    ], fill=(255, 255, 255), outline=None)
    
    # Цвета для треугольников (яркие цвета)
    triangle_colors = [
        (255, 50, 50),    # Красный
        (255, 150, 0),    # Оранжевый
        (50, 255, 50),    # Зеленый
        (50, 150, 255),   # Синий
        (200, 50, 255),   # Фиолетовый
    ]
    
    # Количество треугольников вокруг круга
    num_triangles = 32
    
    # Размер треугольников
    triangle_size = circle_radius * 0.12
    
    # Расстояние от центра до основания треугольника (на краю круга)
    triangle_distance = circle_radius
    
    # Рисуем треугольники вокруг круга
    for i in range(num_triangles):
        # Угол для текущего треугольника
        angle = 2 * math.pi * i / num_triangles
        
        # Выбираем цвет (чередуем цвета)
        color_index = i % len(triangle_colors)
        triangle_color = triangle_colors[color_index]
        
        # Координаты центра треугольника на краю круга
        triangle_center_x = center_x + triangle_distance * math.cos(angle)
        triangle_center_y = center_y + triangle_distance * math.sin(angle)
        
        # Треугольник направлен острием внутрь (к центру круга)
        # Вершина треугольника направлена к центру круга
        tip_x = center_x + (triangle_distance - triangle_size) * math.cos(angle)
        tip_y = center_y + (triangle_distance - triangle_size) * math.sin(angle)
        
        # Основание треугольника перпендикулярно радиусу
        # Вектор перпендикулярный радиусу
        perp_angle = angle + math.pi / 2
        base_half_width = triangle_size * 0.6
        
        base_left_x = triangle_center_x + base_half_width * math.cos(perp_angle)
        base_left_y = triangle_center_y + base_half_width * math.sin(perp_angle)
        
        base_right_x = triangle_center_x - base_half_width * math.cos(perp_angle)
        base_right_y = triangle_center_y - base_half_width * math.sin(perp_angle)
        
        # Координаты треугольника
        triangle_points = [
            (int(tip_x), int(tip_y)),           # Вершина (направлена внутрь)
            (int(base_left_x), int(base_left_y)), # Левая точка основания
            (int(base_right_x), int(base_right_y)) # Правая точка основания
        ]
        
        # Рисуем треугольник
        draw.polygon(triangle_points, fill=triangle_color, outline=None)
    
    # Рисуем буквы "AI" в центре круга
    # Размер шрифта зависит от размера иконки (увеличен)
    font_size = int(size * 0.35)
    
    try:
        # Пытаемся использовать системный шрифт
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        try:
            # Альтернативный шрифт для Windows
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
        except:
            # Если не удалось загрузить шрифт, используем стандартный
            font = ImageFont.load_default()
    
    # Текст "AI"
    text = "AI"
    
    # Получаем размеры текста для центрирования
    try:
        # Используем textbbox для более точного определения размеров
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        # Получаем смещение для точного центрирования
        text_offset_x = bbox[0]
        text_offset_y = bbox[1]
    except:
        # Для старых версий PIL
        try:
            text_width, text_height = draw.textsize(text, font=font)
            text_offset_x = 0
            text_offset_y = 0
        except:
            # Если и это не работает, используем приблизительные значения
            text_width = font_size * len(text) * 0.6
            text_height = font_size
            text_offset_x = 0
            text_offset_y = 0
    
    # Позиция текста (точно центрированная с учетом смещения)
    text_x = center_x - text_width // 2 - text_offset_x
    text_y = center_y - text_height // 2 - text_offset_y
    
    # Рисуем текст черным цветом на белом круге
    draw.text((text_x, text_y), text, fill=(0, 0, 0), font=font)
    
    return img

# Размеры иконки
sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
icons = [draw_icon(s) for s, _ in sizes]

# Изображения уже в RGB режиме, просто убеждаемся
rgb_icons = []
for icon in icons:
    # Убеждаемся, что изображение в RGB режиме (не палитра)
    if icon.mode != "RGB":
        rgb_img = icon.convert("RGB")
    else:
        rgb_img = icon
    rgb_icons.append(rgb_img)

# Сохранение с явным указанием формата и цветов
try:
    rgb_icons[0].save(
        "app.ico",
        format="ICO",
        sizes=sizes,
        append_images=rgb_icons[1:]
    )
    print("[OK] Иконка 'app.ico' создана!")
    print("   Дизайн: белый круг с разноцветными треугольниками и буквами AI")
    print("   Цвета треугольников: красный, оранжевый, зеленый, синий, фиолетовый")
    print("   Количество треугольников: 32")
    print("   Текст в центре: AI (черный на белом фоне)")
except Exception as e:
    print(f"[ERROR] Ошибка при сохранении: {e}")
    # Альтернативный способ - сохранить каждое изображение отдельно
    print("Попытка альтернативного метода сохранения...")
    rgb_icons[0].save("app.ico", format="ICO")
    print("[OK] Иконка 'app.ico' создана (только один размер)")
