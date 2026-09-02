import os
import re
import glob

directory = r'c:\Users\ABT-PC\Desktop\AcilBir.com\AcilBir-Generator\.github\workflows'

# We want to remove the block that starts with UPDATE_URL=... and ends with the sed replacements for UPDATE_URL.
# It usually looks like:
#           UPDATE_URL=...
#           if ...
#           fi
#           sed ... UPDATE_URL ...
# We can use a regex to match the lines containing UPDATE_URL. Since it's a contiguous block, we can just delete any line containing UPDATE_URL.

for filename in glob.glob(os.path.join(directory, '*.yml')):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    modified = False
    for line in lines:
        if 'UPDATE_URL' in line:
            modified = True
            continue
        new_lines.append(line)
        
    if modified:
        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"Cleaned {os.path.basename(filename)}")
