import urllib.request, os  
url='https://github.com/google/fonts/raw/main/ofl/notonaskharabic/NotoNaskhArabic-Regular.ttf'  
path='NotoNaskhArabic-Regular.ttf'  
urllib.request.urlretrieve(url, path)  
print('exists=', os.path.exists(path), 'size=', os.path.getsize(path))  
