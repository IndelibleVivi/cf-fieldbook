"""Synthetic fonts verify PDF container repair without redistributing system fonts."""
import io
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

from fontTools.cffLib import FDArrayIndex, FDSelect, FontDict
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
import pydyf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from render import embed_compact_cid_fonts


def synthetic_font(cid=True, identity=True):
    builder = FontBuilder(1000, isTTF=False)
    order = ['.notdef', 'cid00001', 'cid00002' if identity else 'cid00009']
    builder.setupGlyphOrder(order)
    builder.setupCharacterMap({65: order[1], 0x4E2D: order[2]})
    builder.setupHorizontalMetrics({name: (500, 0) for name in order})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({'familyName': 'SyntheticCID', 'styleName': 'Regular',
                            'psName': 'SyntheticCID-Regular'})
    builder.setupOS2()
    builder.setupPost()
    chars = {}
    for name in order:
        pen = T2CharStringPen(500, None)
        pen.moveTo((100, 0))
        pen.lineTo((250, 700))
        pen.lineTo((400, 0))
        pen.closePath()
        chars[name] = pen.getCharString()
    builder.setupCFF('SyntheticCID-Regular', {}, chars, {})
    font = builder.font
    if cid:
        top = font['CFF '].cff.topDictIndex[0]
        top.ROS = ('Adobe', 'Identity', 0)
        fd = FontDict()
        fd.Private = top.Private
        top.FDArray = FDArrayIndex()
        top.FDArray.append(fd)
        top.FDSelect = FDSelect()
        top.FDSelect.gidArray = [0] * len(order)
        top.FDSelect.format = 3
    output = io.BytesIO()
    font.save(output)
    return output.getvalue()


class PDFFontTests(unittest.TestCase):
    def test_identity_cid_embeds_the_exact_cff_table_and_preserves_other_objects(self):
        from fontTools.ttLib import TTFont
        data = synthetic_font()
        with TTFont(io.BytesIO(data)) as font:
            expected = font.reader['CFF ']
        stream = pydyf.Stream([data], {'Subtype': '/OpenType'}, compress=True)
        page = pydyf.Stream([b'page drawing commands'], compress=True)
        unicode_map = pydyf.Stream([b'Unicode mapping'])
        outline = pydyf.Dictionary({'Title': pydyf.String('Chapter')})
        pdf = SimpleNamespace(objects=[page, stream, unicode_map, outline])
        embed_compact_cid_fonts(None, pdf)
        self.assertEqual(stream.extra['Subtype'], '/CIDFontType0C')
        self.assertEqual(stream.stream, [expected])
        self.assertTrue(stream.compress)
        self.assertEqual(page.stream, [b'page drawing commands'])
        self.assertEqual(unicode_map.stream, [b'Unicode mapping'])
        self.assertEqual(outline['Title'].string, 'Chapter')
        # A second call must not parse compact CFF as an OpenType file.
        embed_compact_cid_fonts(None, pdf)
        self.assertEqual(stream.stream, [expected])

    def test_other_font_containers_and_charsets_are_unchanged(self):
        for data, subtype in [(synthetic_font(cid=False), '/OpenType'),
                              (synthetic_font(identity=False), '/OpenType'),
                              (b'true type font data', None)]:
            with self.subTest(subtype=subtype, prefix=data[:4]):
                extra = {} if subtype is None else {'Subtype': subtype}
                expected_extra = dict(extra)
                stream = pydyf.Stream([data], extra)
                embed_compact_cid_fonts(None, SimpleNamespace(objects=[stream]))
                self.assertEqual(stream.stream, [data])
                self.assertEqual(dict(stream.extra), expected_extra)


if __name__ == '__main__':
    unittest.main()
