import os, re

path = r'C:\Users\luffy\Downloads\enter\Food-Court-Reservation-System-Odoo\foodcourt\views'
for f in os.listdir(path):
    if f.endswith('.xml'):
        filepath = os.path.join(path, f)
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Matches <group expand="0" string="Group By"> ... </group>
        new_content = re.sub(r'[ \t]*<group expand="0" string="Group By">.*?</group>\r?\n?', '', content, flags=re.DOTALL)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(new_content)
            print(f'Stripped Group By from {f}')
