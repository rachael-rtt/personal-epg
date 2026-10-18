import gzip
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from merge_epg import merge, read_xml, timestamp

NOW = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)


def xml(channel, events):
    return ('<tv><channel id="' + channel + '"><display-name>Test</display-name></channel>'
            + ''.join('<programme channel="' + channel + '" start="' + start + '" stop="'
                      + stop + '"><title>' + title + '</title></programme>'
                      for start, stop, title in events) + '</tv>').encode()


class MergerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def source(self, name, data, zipped=False):
        path = Path(self.tmp.name) / name
        path.write_bytes(gzip.compress(data) if zipped else data)
        return {'name': name, 'url': str(path)}

    def test_gzip_detected_without_extension(self):
        src = self.source('compressed', xml('a', []), True)
        self.assertEqual(read_xml(src['url']).tag, 'tv')

    def test_priority_dedup_gap_fill_and_timezone(self):
        first = self.source('first', xml('a', [('20261018120000 +0000','20261018130000 +0000','First')]))
        second = self.source('second', xml('a', [
            ('20261018140000 +0200','20261018150000 +0200','First'),
            ('20261018123000 +0000','20261018133000 +0000','Conflict'),
            ('20261018130000 +0000','20261018140000 +0000','Next')]))
        root, report, _ = merge({'a':'A'}, [first, second], {}, NOW)
        self.assertEqual([p.findtext('title') for p in root.findall('programme')], ['First','Next'])
        self.assertEqual(len(root.findall('channel')), 1)
        self.assertEqual(report['overlaps_skipped'], 1)

    def test_mapping_preserves_original_playlist_id(self):
        src = self.source('pluto', xml('Pluto TV Comedy.us', [('20261018120000 +0000','20261018130000 +0000','Comedy')]))
        mappings = {'PlutoTVComedy.us@US':{'source':'pluto','source_id':'Pluto TV Comedy.us'}}
        root, report, _ = merge({'PlutoTVComedy.us@US':'Comedy','PlutoTVComedy.us@CA':'Comedy CA'}, [src], mappings, NOW)
        self.assertEqual(root.find('programme').get('channel'), 'PlutoTVComedy.us@US')
        self.assertEqual(report['covered_ids'], 1)
        self.assertEqual(report['unmatched'][0]['playlist_id'], 'PlutoTVComedy.us@CA')

    def test_name_similarity_is_only_a_suggestion(self):
        src = self.source('src', xml('Test.us', [('20261018120000 +0000','20261018130000 +0000','Show')]))
        _, report, _ = merge({'Test.us@SD':'Test'}, [src], {}, NOW)
        self.assertEqual(report['covered_ids'], 0)
        self.assertTrue(report['unmatched'][0]['candidates_for_review'])

    def test_stale_and_ambiguous_time_not_covered(self):
        src = self.source('src', xml('a', [('20261017120000 +0000','20261017130000 +0000','Old'),
                                         ('20261018120000','20261018130000','Ambiguous')]))
        _, report, _ = merge({'a':'A'}, [src], {}, NOW)
        self.assertEqual(report['covered_ids'], 0)
        self.assertEqual(report['invalid_programmes_skipped'], 1)

    def test_bad_source_aborts_build(self):
        src = self.source('bad', b'<html>Maintenance</html>')
        with self.assertRaises(ValueError):
            merge({'a':'A'}, [src], {}, NOW)

    def test_timezone_conversion(self):
        self.assertEqual(timestamp('20261018140000 +0200'), NOW)


if __name__ == '__main__':
    unittest.main()
