"""Fit existing Egyptian font outlines to review cards without changing glyph geometry."""
from collections import Counter
import hashlib
import html
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

from audit_shape_historical_buckets import protect
from build_shape_pictorial_review import EDITOR, read, sha
from build_shape_keyboard_full import save

ASSETS = EDITOR / 'data/pictorial-glyph-previews'
REPORT = EDITOR / 'data/pictorial-glyph-previews.json'


def outline_svg(glyphs, name):
    bounds = BoundsPen(glyphs)
    glyphs[name].draw(bounds)
    if bounds.bounds is None:
        return None, None
    x0, y0, x1, y1 = bounds.bounds
    width, height = x1-x0, y1-y0
    if min(width, height) <= 0:
        return None, bounds.bounds
    padding = max(width, height)*.06
    path = SVGPathPen(glyphs)
    glyphs[name].draw(TransformPen(path, (1, 0, 0, -1, 0, 0)))
    view = (x0-padding, -y1-padding, width+2*padding, height+2*padding)
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="'+ ' '.join(f'{v:.6f}' for v in view)+'"><path fill="black" d="'+html.escape(path.getCommands(), quote=True)+'"/></svg>\n'
    return svg, bounds.bounds


def build():
    protected = protect()
    source = EDITOR / 'data/pictorial-intake-review.json'
    review = read(source)
    targets = [r for r in review['records'] if r['font']['source']=='EgyptologyExtended.ttf']
    ASSETS.mkdir(parents=True, exist_ok=True)
    fonts, previews, counts = {}, {}, Counter()
    try:
        for row in targets:
            file = row['font']['file']
            if file not in fonts:
                fonts[file] = TTFont(EDITOR / 'fonts' / file)
            font = fonts[file]
            cmap = font.getBestCmap()
            if row['cp'] not in cmap:
                counts['missing'] += 1
                continue
            svg, bounds = outline_svg(font.getGlyphSet(), cmap[row['cp']])
            if svg is None:
                counts['empty'] += 1
                continue
            ratio = max(bounds[2]-bounds[0], bounds[3]-bounds[1])/font['head'].unitsPerEm
            kind = 'tiny' if ratio < .15 else 'large' if ratio >= 1.5 else 'normal'
            counts[kind] += 1
            data = svg.encode('utf-8')
            name = f'{row["cp"]:05X}-{hashlib.sha256(data).hexdigest()[:12]}.svg'
            target = ASSETS / name
            if target.exists():
                assert target.read_bytes() == data
            else:
                target.write_bytes(data)
            previews[str(row['cp'])] = {'url':'data/pictorial-glyph-previews/'+name,
                'sourceFont':file, 'sourceFontSHA256':sha(EDITOR/'fonts'/file),
                'bounds':list(bounds), 'emRatio':ratio, 'problem':kind,
                'kind':'original-outline-uniform-fit', 'geometryChanged':False}
    finally:
        for font in fonts.values():
            font.close()
    result = {'format':'pictorial-glyph-previews-v1', 'date':'2026-10-23',
        'sourceReviewVersion':review['version'], 'previews':previews,
        'statistics':dict(counts), 'sourceReportSHA256':sha(source),
        'note':'Same original outline, uniform fit only. Does not certify semantic glyph mapping or alter detector inputs.',
        'attribution':'Egyptology Extended by Land of Kemet; based on JSesh glyphs by Serge Rosmorduc and Serge J.P. Thomas; CeCILL v2.1.',
        'sourceUrl':'https://github.com/LumabyteCo/egyptology-extended-font',
        'allocationChanged':False,'runtimeDeployed':False}
    assert protect()==protected
    save(REPORT,result)
    print({'previews':len(previews),**dict(counts)})
    return result


if __name__=='__main__':build()
