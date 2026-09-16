from pathlib import Path

path = Path('admin.html')
text = path.read_text(encoding='utf-8')
marker = '<script src="admin-scheduler.js"></script>'
if marker not in text:
    text = text.replace('</body>', marker + '\n</body>', 1)
    path.write_text(text, encoding='utf-8')
