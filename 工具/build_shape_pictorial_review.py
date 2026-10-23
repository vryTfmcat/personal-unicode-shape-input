"""Build a complete, non-migrating pictorial intake review from the pinned corpus."""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from audit_shape_historical_buckets import PROJECT, SOURCE, protect
from build_shape_keyboard_full import save

VERSION = 'pictorial-intake-20261022-v1'
OUT = SOURCE.parent / '20261022-pictorial-intake-review-v1'
EDITOR = PROJECT / '原型/键位编辑器'
UCD = PROJECT / '数据/Unicode精选/UCD-17.0.0'
EXPLICIT_YES = set(map(ord, '😸𓁞𓀥𓆟☀☁☾'))
EXPLICIT_NO = set(map(ord, '♥♡♀♂♠♣♦'))
EXAMPLES = set(map(ord, '🏇👪🏕'))
GROUPS = {
    'A': '人物与动作', 'B': '人物与动作', 'C': '人物与复合形象',
    'D': '身体部位', 'E': '动物', 'F': '动物部位', 'G': '鸟类',
    'H': '鸟类部位', 'I': '动物', 'K': '鱼类', 'L': '昆虫',
    'M': '植物', 'N': '自然物象', 'O': '建筑与场所', 'P': '交通与船只',
    'Q': '家具与物品', 'R': '物品与标志', 'S': '服饰与物品',
    'T': '工具与物品', 'U': '工具与物品', 'V': '绳索与物品',
    'W': '容器与物品', 'X': '食物', 'Y': '书写与物品',
}
# These are retrieval hints only. No name or block implies visual acceptance.
HINTS = [
    ('人脸与表情', r'FACE|SMILE|SMILING|FROWN|GRIN|KISS|EMOTION|PENSIVE|SLEEPY|NERD|ZANY|MONOCLE'),
    ('人物与动作', r'MAN\b|WOMAN|PERSON|PEOPLE|FAMILY|CHILD|BABY|BOY\b|GIRL|COUPLE|BRIDE|PRINCESS|PRINCE\b|SANTA|DANCER|DANCING|RUNNER|WALKING|SWIMMER|BICYCLIST|SURFER|SNOWBOARDER|FENCER|JUGGLING|WRESTL|CARTWHEEL|GYMNAST|GOLFER|CLIMB|YOGA|MAGE|VAMPIRE|ZOMBIE|MERMAID|MERPERSON|FAIRY|ELF\b|GENIE|TROLL|HERO|VILLAIN|PREGNANT'),
    ('身体部位', r'HAND|FINGER|THUMB|FIST|FOOT|FOOTPRINT|LEG\b|ARM\b|EYE\b|EYES\b|EAR\b|NOSE|MOUTH|LIPS|TONGUE|BRAIN|TOOTH|BONE|LUNG|ANATOMICAL HEART|BUST|BREAST'),
    ('动物', r'ANIMAL|CAT\b|DOG\b|LION|TIGER|HORSE|COW\b|OX\b|BULL|PIG\b|BOAR|SHEEP|RAM\b|GOAT|CAMEL|LLAMA|DEER|MOOSE|BISON|BEAR|WOLF|FOX\b|RABBIT|HARE|MOUSE|RAT\b|HAMSTER|MONKEY|GORILLA|ORANGUTAN|ELEPHANT|RHINO|HIPPO|GIRAFFE|ZEBRA|KANGAROO|KOALA|PANDA|BADGER|BEAVER|OTTER|SLOTH|BAT\b|SKUNK|RACCOON|HEDGEHOG|DONKEY|UNICORN|DRAGON|DINOSAUR|SAUROPOD|REX\b|BIRD|DOVE|EAGLE|DUCK|GOOSE|SWAN|OWL\b|FLAMINGO|PEACOCK|PARROT|PENGUIN|CHICK|ROOSTER|TURKEY|DODO|CROW|PHOENIX|FISH|SHARK|WHALE|DOLPHIN|SEAL\b|OCTOPUS|SQUID|CRAB|LOBSTER|SHRIMP|PRAWN|JELLYFISH|OYSTER|CORAL|SHELL|TURTLE|SNAKE|LIZARD|CROCODILE|FROG|SNAIL|BUTTERFLY|BUG\b|BEETLE|LADY|ANT\b|BEE\b|SPIDER|SCORPION|MOSQUITO|FLY\b|WORM|CRICKET|FEATHER|PAW|WING'),
    ('植物', r'PLANT|TREE|PALM|CACTUS|CLOVER|LEAF|LEAVES|HERB|SEEDLING|SPROUT|FLOWER|BLOSSOM|BOUQUET|ROSE|TULIP|SUNFLOWER|HIBISCUS|LOTUS|HYACINTH|MUSHROOM|SHEAF|SHAMROCK|BAMBOO|WOOD|LOG\b'),
    ('自然物象', r'SUN\b|SUNRISE|SUNSET|CLOUD|MOON|RAIN|SNOW|WIND|CYCLONE|TORNADO|FOG|LIGHTNING|THUNDER|COMET|METEOR|VOLCANO|MOUNTAIN|WAVE|EARTH|GLOBE|RAINBOW|DROPLET|FIRE\b|FLAME|WATER|ROCK\b|STONE\b|PLANET|GALAXY|MILKY WAY'),
    ('交通工具', r'CAR\b|TAXI|AUTOMOBILE|BUS\b|TRUCK|LORRY|TRACTOR|VEHICLE|MOTOR|SCOOTER|BICYCLE|TRICYCLE|TRAIN|RAIL|LOCOMOTIVE|TRAM|TROLLEY|MONORAIL|AIRPLANE|AEROPLANE|AIRCRAFT|HELICOPTER|ROCKET|SATELLITE|SHIP|BOAT|CANOE|FERRY|SAIL|CABLEWAY|GONDOLA|CHAIRLIFT|SKATEBOARD|SKATE\b|SLED|WHEELCHAIR|RICKSHAW'),
    ('建筑与场所', r'BUILDING|HOUSE|HOME\b|HOSPITAL|SCHOOL|HOTEL|CASTLE|CHURCH|MOSQUE|SYNAGOGUE|TEMPLE|SHRINE|PAGODA|HUT\b|TENT|CAMPING|STADIUM|BRIDGE|TOWER|FACTORY|BANK\b|POST OFFICE|STORE|SHOP\b|FOUNTAIN|STATUE|LANDSCAPE|PARK\b|BEACH|ISLAND'),
    ('食物与饮品', r'FOOD|FRUIT|APPLE|PEAR\b|PEACH|CHERRY|CHERRIES|GRAPE|MELON|BANANA|PINEAPPLE|MANGO|KIWI|COCONUT|LEMON|LIME\b|BERRY|BERRIES|TOMATO|AVOCADO|OLIVE|CORN|CARROT|POTATO|ONION|GARLIC|PEPPER|BROCCOLI|CUCUMBER|LETTUCE|PEA POD|BEANS|CHESTNUT|PEANUT|BREAD|BAGUETTE|BAGEL|CROISSANT|PANCAKE|WAFFLE|SANDWICH|PIZZA|HAMBURGER|FRIES|HOT DOG|TACO|BURRITO|FALAFEL|DUMPLING|SUSHI|RICE|NOODLE|SPAGHETTI|CURRY|STEW|SOUP|MEAT|POULTRY|BACON|STEAK|CHEESE|EGG\b|COOKING|COOKIE|CAKE|CANDY|CHOCOLATE|LOLLIPOP|CUSTARD|ICE CREAM|HONEY|SALT|BUTTER|CUP\b|TEA\b|COFFEE|BEER|WINE|SAKE|COCKTAIL|DRINK|BOTTLE|MILK'),
    ('工具与日常物品', r'ANCHOR|UMBRELLA|SCISSORS|PENCIL|PEN\b|CRAYON|BRUSH|HAMMER|PICK\b|AXE|WRENCH|SCREW|NUT AND BOLT|GEAR|CHAIN|LINK\b|LADDER|HOOK|MAGNET|TOOL|SHOVEL|SAW\b|KNIFE|DAGGER|SWORD|BOW AND ARROW|PISTOL|GUN\b|BOMB|SHIELD|BOOMERANG|KEY\b|LOCK|BELL|CLOCK|WATCH|HOURGLASS|THERMOMETER|SCALE|COMPASS|TELESCOPE|MICROSCOPE|SYRINGE|PILL|STETHOSCOPE|CRUTCH|BANDAGE|TEST TUBE|PETRI|DNA|BOOK|SCROLL|PAPER|ENVELOPE|MAIL|LETTER BOX|NEWSPAPER|NOTEBOOK|CALENDAR|CLIP|RULER|SCROLL|FOLDER|CABINET|CHAIR|SEAT|BED\b|COUCH|SOFA|DOOR|WINDOW|MIRROR|TOILET|BATH|SHOWER|BROOM|SOAP|SPONGE|BUCKET|BASKET|SAFETY PIN|EXTINGUISHER|CANDLE|LAMP|LIGHT BULB|FLASHLIGHT|ELECTRIC|BATTERY|PLUG|TELEPHONE|RECEIVER|MOBILE PHONE|COMPUTER|KEYBOARD|PRINTER|MOUSE|TRACKBALL|CAMERA|TELEVISION|RADIO|VIDEOCASSETTE|VIDEOTAPE|DISC|DISK|JOYSTICK|VIDEO GAME|MICROPHONE|HEADPHONE|SPEAKER|MEGAPHONE|DRUM|GUITAR|VIOLIN|TRUMPET|SAXOPHONE|FLUTE|HARP|ACCORDION|BANJO|PIANO|MUSICAL KEYBOARD|CLOTHING|SHIRT|DRESS|COAT|JACKET|VEST|JEANS|PANTS|SHORTS|SOCK|GLOVE|SCARF|HAT\b|CAP\b|CROWN|HELMET|BOOT|SHOE|SANDAL|KIMONO|SARI|SWIMSUIT|BIKINI|HANDBAG|POUCH|PURSE|BRIEFCASE|LUGGAGE|BACKPACK|GLASSES|GOGGLES|RING\b|GEM|DIAMOND|NECKLACE|BEAD|LIPSTICK|COMB|RAZOR|THREAD|NEEDLE|YARN|KNOT|BALL\b|RACKET|BAT AND|BADMINTON|HOCKEY|SKI|FISHING|BOWLING|BILLIARD|GOLF|TROPHY|MEDAL|DICE|DIE FACE|CHESS|PUZZLE|TEDDY|KITE|YO-YO|DOLL|BALLOON|PARTY|GIFT|RIBBON|FIREWORK|SPARKLER|JACK-O-LANTERN|CHRISTMAS|FLAG|COIN|MONEY|BANKNOTE|CREDIT CARD|POOP|COFFIN|URN|AMPhORA|PACKAGE|WHEEL\b'),
]
HINTS = [(category, re.compile(r'(?<![A-Z])(?:' + pattern + r')(?![A-Z])', re.I)) for category, pattern in HINTS]
ABSTRACT = re.compile(r'HEART(?!.*ANATOMICAL)|ARROW|ASTERISK|STAR(?!.*FISH)|SPARKLE|CIRCLE|SQUARE|TRIANGLE|DIAMOND(?!.*GEM)|LOZENGE|SUIT|GENDER|MALE SIGN|FEMALE SIGN|TRANSGENDER|INFINITY|RECYCLE|RECYCLING|RADIOACTIVE|BIOHAZARD|PEACE SYMBOL|YIN YANG|TRIGRAM|HEXAGRAM|DIGRAM|MONOGRAM|PENTAGRAM|HEXAGRAM|CROSS|SWASTI|SVASTI|CHECK MARK|BALLOT|EXCLAMATION|QUESTION MARK|PUNCTUATION|MULTIPLICATION|DIVISION|PLUS SIGN|MINUS SIGN|EQUALS|NUMBER SIGN|INPUT SYMBOL|KEYCAP|REGIONAL INDICATOR|VARIATION SELECTOR|EMOJI MODIFIER|SKIN TONE|SQUARED|CIRCLED|NEGATIVE .*LETTER', re.I)
GEOMETRIC_BLOCKS = {'Box Drawing', 'Block Elements', 'Braille Patterns', 'Geometric Shapes',
    'Geometric Shapes Extended', 'Symbols for Legacy Computing', 'Symbols for Legacy Computing Supplement',
    'Yijing Hexagram Symbols', 'Tai Xuan Jing Symbols', 'Counting Rod Numerals',
    'Sutton SignWriting', 'Musical Symbols', 'Byzantine Musical Symbols', 'Ancient Greek Musical Notation',
    'Enclosed Alphanumerics', 'Enclosed Alphanumeric Supplement', 'Enclosed CJK Letters and Months',
    'Enclosed Ideographic Supplement', 'CJK Compatibility', 'Kangxi Radicals', 'CJK Radicals Supplement',
    'Ideographic Description Characters', 'Alchemical Symbols', 'Control Pictures', 'Optical Character Recognition',
    'Letterlike Symbols', 'Arrows', 'Supplemental Arrows-A', 'Supplemental Arrows-B', 'Supplemental Arrows-C'}
PICTORIAL_BLOCKS = {'Miscellaneous Symbols', 'Dingbats', 'Miscellaneous Symbols and Pictographs',
    'Emoticons', 'Transport and Map Symbols', 'Supplemental Symbols and Pictographs',
    'Symbols and Pictographs Extended-A', 'Chess Symbols', 'Miscellaneous Technical',
    'Symbols for Legacy Computing', 'Symbols for Legacy Computing Supplement',
    'Ancient Symbols', 'Miscellaneous Symbols and Arrows', 'Ornamental Dingbats'}
TECHNICAL_OBJECTS = set(map(ord, '⌂⌕⌚⌛⌨⍾⏰⏱⏲⏳⏿'))


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_ucd():
    names = {}
    with (UCD / 'UnicodeData.txt').open(encoding='utf-8', newline='') as f:
        for row in csv.reader(f, delimiter=';'):
            names[int(row[0], 16)] = (row[1], row[2])
    blocks = []
    for line in (UCD / 'Blocks.txt').read_text(encoding='utf-8').splitlines():
        line = line.partition('#')[0].strip()
        if not line:
            continue
        extent, name = line.split(';')
        lo, hi = (int(x, 16) for x in extent.strip().split('..'))
        blocks.append((lo, hi, name.strip()))
    return names, blocks


def category_hint(name):
    if re.search(r'DIE FACE|DICE|CHESS', name):
        return '游戏与棋子'
    return next((c for c, pattern in HINTS if pattern.search(name)), None)


def classify(cp, name, gc, block):
    if cp in EXPLICIT_YES:
        return 'confirmed', ('象形·鱼类' if cp == 0x1319F else '象形·人物与动作' if cp in (0x1305E, 0x13025) else category_hint(name)) or '人物与动物形象', '用户直接举例确认收入'
    if cp in EXPLICIT_NO:
        return 'exclude', '已明确排除', '用户直接举例确认不收入'
    if 'EGYPTIAN HIEROGLYPH' in name and ('FORMAT' in block.upper() or any(s in name for s in ('BLANK', 'LOST SIGN'))):
        return 'exclude', '格式与占位', '格式控制／空白／缺损占位，不是具体物象'
    if 'EGYPTIAN HIEROGLYPH' in name:
        match = re.search(r'HIEROGLYPH ([A-Z]+)\d', name)
        group = match.group(1) if match else None
        return 'boundary', ('象形·' + GROUPS[group]) if group in GROUPS else '象形·形象待辨', '逐字看图；编号分组只作检索提示，不等于可辨认或已收入'
    if 'ANATOLIAN HIEROGLYPH' in name:
        return 'boundary', '象形·安纳托利亚待辨', '需逐字确认可见具体形象；不猜名称与读音'
    if block in ('Linear B Ideograms', 'Meroitic Hieroglyphs'):
        return 'boundary', '象形·其他古文字待辨', '保留可能可辨认的物象；不能按文字的语义或整区收入'
    if cp in EXAMPLES:
        return 'propose', '人物与场景', '完整图像已确认可收入；本字仍列入逐字初稿'
    if cp in (0x2609, 0x2641, 0x267E):
        return 'boundary', '抽象图形与物象边界', '圆点／圆加十字／永久纸标志：名称涉及物象，但字形可能只宜按抽象结构查找'
    if name == 'ANATOMICAL HEART':
        return 'propose', '身体部位', '具体器官图像；不同于已排除的抽象心形，仍待逐字审核'
    hint = category_hint(name)
    concrete_compound = bool(hint and re.search(r'FACE|MAN\b|WOMAN|PERSON|PEOPLE|FAMILY|HAND|SKULL|SWORDS|BONES', name))
    if ABSTRACT.search(name) and not concrete_compound:
        return 'exclude', '抽象图形与标志', '按已定边界暂排除抽象形；系列推广待用户核对'
    if block in GEOMETRIC_BLOCKS and not (hint and block.startswith('Symbols for Legacy Computing')):
        return 'exclude', '几何／文字／专业记号', '该类默认保留原查法；不按名称指代的物品直接收入'
    if gc == 'So' and hint and block in PICTORIAL_BLOCKS and (block != 'Miscellaneous Technical' or cp in TECHNICAL_OBJECTS):
        return 'propose', hint, 'Unicode名称检索到具体物象；机器初稿，必须按实际字形审核'
    if gc == 'So':
        return 'boundary', '其他符号·防漏核对', '名称未能可靠判断具体物象；保留在防漏队列，不自动收入'
    if gc == 'Sk' and 'EMOJI MODIFIER' in name:
        return 'exclude', '组合修饰符', '肤色修饰符不作为独立拟物图像'
    return None


def build(refresh_generated=False):
    if OUT.exists() and not refresh_generated:
        raise FileExistsError('不覆盖已有拟物收入初稿')
    if OUT.exists():
        assert read(OUT/'拟物收入全量初稿.json')['version'] == VERSION
    protected = protect()
    index = read(SOURCE / '发布核对索引.json')
    ordinary = {r['cp']: r for r in index['records']}
    memberships = {cp: ['ordinary'] for cp in ordinary}
    for label, values in list(index['collections'].items()) + [('unclassified', index['unclassified'])]:
        for cp in values:
            memberships.setdefault(cp, []).append(label)
    assert len(memberships) == 159345
    names, blocks = load_ucd()
    manifest = read(EDITOR / 'fonts/manifest.json')
    coverage = {cp: {'file': f['file'], 'kind': f['kind'], 'source': f['source']} for f in manifest['faces'] for cp in f['codepoints']}
    records = []
    non_candidates = Counter()
    for cp in sorted(memberships):
        name, gc = names.get(cp, ('<UCD range member>', 'Lo'))
        block = next((b for lo, hi, b in blocks if lo <= cp <= hi), 'Unknown')
        decision = classify(cp, name, gc, block)
        if not decision:
            non_candidates['非独立符号／非象形候选'] += 1
            continue
        queue, category, reason = decision
        row = ordinary.get(cp, {})
        font = coverage.get(cp)
        assert font, f'缺少本地字形：U+{cp:04X}'
        assert (EDITOR / 'fonts' / font['file']).is_file()
        records.append({'cp': cp, 'char': chr(cp), 'name': name, 'block': block, 'category': category,
            'proposal': queue, 'reason': reason, 'membership': memberships[cp],
            'oldBucket': row.get('bucket'), 'oldCodes': row.get('codes', []),
            'preview': row.get('preview'), 'font': font, 'humanReviewed': cp in EXPLICIT_YES | EXPLICIT_NO})
    stats = dict(Counter(r['proposal'] for r in records))
    assert sum(stats.values()) + sum(non_candidates.values()) == len(memberships)
    assert all(next(r for r in records if r['cp'] == cp)['proposal'] == 'confirmed' for cp in EXPLICIT_YES)
    assert all(next(r for r in records if r['cp'] == cp)['proposal'] == 'exclude' for cp in EXPLICIT_NO)
    report = {'version': VERSION, 'date': '2026-10-22', 'sourceIndexSHA256': sha(SOURCE / '发布核对索引.json'),
        'sourceFiles': {str(p.relative_to(PROJECT)): sha(p) for p in (UCD/'UnicodeData.txt', UCD/'Blocks.txt', EDITOR/'fonts/manifest.json')},
        'scope': {'sourceIdentities': len(memberships), 'ordinary': len(ordinary),
            'listedSymbols': len(records), 'outsidePictorialRetrieval': sum(non_candidates.values()),
            'singleCodepointOnly': True, 'unicodeVersion': '17.0.0'},
        'statistics': stats, 'categories': dict(Counter(r['category'] for r in records)),
        'policy': {'firstKey': 't', 'firstKeyHumanAccepted': True, 'exclusiveAfterIndividualApproval': True,
            'recognizableObjects': True, 'recognizableHieroglyphs': True, 'multiObjectScenes': True,
            'geometricHeartsExcluded': True, 'sunCloudMoonAccepted': True,
            'noWholeBlockAdmission': True, 'secondKeysAssigned': False},
        'limitations': ['名称与区段仅用于召回，不是字形人工判断。',
            '象形文字和其他防漏候选需看图逐字判断，尚未整段收入。',
            '未穷尽所有文字字符中偶然像物体的形状；中文与普通表音文字不因语义收入。',
            '仅覆盖现有码表159345个单码位身份；组合Emoji、ZWJ序列不在本轮范围。',
            '本地审阅结果是待汇总草稿，导出后再回写现有人工审议；不改编码或部署。'],
        'records': records, 'protectedHashes': protected, 'allocationChanged': False, 'runtimeDeployed': False}
    assert protected == protect()
    save(OUT / '拟物收入全量初稿.json', report)
    save(EDITOR / 'data/pictorial-intake-review.json', {k: v for k, v in report.items() if k != 'protectedHashes'})
    with (OUT / '拟物收入全量初稿.tsv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(['码位', '字符', '初稿队列', '分类提示', '名称', '原主桶', '原码', '判断依据', '我的判断'])
        for r in records:
            writer.writerow([f"U+{r['cp']:04X}", r['char'], r['proposal'], r['category'], r['name'], r['oldBucket'] or '', ' '.join(r['oldCodes']), r['reason'], ''])
    save(OUT / '验收.json', {'passed': True, 'allCorpusIdentitiesAccounted': True,
        'allListedHaveLocalFonts': True, 'noDuplicateCodepoints': len(records) == len({r['cp'] for r in records}),
        'explicitExamplesPreserved': True, 'protectedInputsUnchanged': protected == protect(),
        'allocationChanged': False, 'runtimeDeployed': False})
    print(json.dumps({'scope': report['scope'], 'statistics': stats}, ensure_ascii=False))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh-generated', action='store_true')
    build(parser.parse_args().refresh_generated)
