"""Package both first-party addon directories; no external addon code is bundled."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
root=Path(__file__).resolve().parent.parent
(root/'release').mkdir(exist_ok=True)
with ZipFile(root/'release'/'LazyCrawler-addon.zip','w',ZIP_DEFLATED) as archive:
    for path in sorted((root/'addon').rglob('*')):
        if path.is_file():archive.write(path,path.relative_to(root/'addon'))
print('Created release/LazyCrawler-addon.zip')
