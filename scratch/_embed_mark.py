import re
s = open('assets/icon/Swimnetics_icon.svg', encoding='utf-8').read()
b64 = re.search(r'base64,([A-Za-z0-9+/=]+)', s).group(1)
uri = 'data:image/png;base64,' + b64
h = open('scratch/website-home-mockup.html', encoding='utf-8').read()
n = h.count('src="swimnetics-mark.svg"')
h = h.replace('src="swimnetics-mark.svg"', 'src="%s"' % uri)
open('scratch/website-home-mockup.html', 'w', encoding='utf-8').write(h)
print('embedded into', n, 'img tags; file', len(h), 'chars')
