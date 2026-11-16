"""Stdlib tests. Set V6_FINAL_EXPERIMENT to run exact trusted-bundle integration tests."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "preparer", Path(__file__).with_name("prepare-v6-final-lab.py")
)
preparer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparer)


class SafetyTests(unittest.TestCase):
    def test_strict_json(self):
        for data in (b'[]', b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                preparer.object_json(data)

    def test_untrusted_manifest_creates_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / "source"
            source.mkdir()
            (source / "final_manifest.json").write_text('{}')
            destination = root / "output"
            with self.assertRaisesRegex(ValueError, "Untrusted revision"):
                preparer.prepare(source, destination)
            self.assertFalse(destination.exists())


@unittest.skipUnless(os.environ.get("V6_FINAL_EXPERIMENT"), "Exact local experiment not supplied")
class TrustedIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / "experiment"
        shutil.copytree(os.environ["V6_FINAL_EXPERIMENT"], self.source)
        self.destination = self.root / "web"

    def test_exact_six_files_no_model_loading_and_no_overwrite(self):
        result = preparer.prepare(self.source, self.destination)
        self.assertFalse(result["model_loaded"])
        self.assertFalse(result["inference_executed"])
        self.assertEqual(result["experiment_hashes_checked"], 41)
        self.assertEqual({path.name for path in self.destination.iterdir()},
                         set(preparer.FILES) | {"web_manifest.json"})
        for name in preparer.FILES:
            self.assertEqual((self.source / name).read_bytes(),
                             (self.destination / name).read_bytes())
        with self.assertRaisesRegex(ValueError, "never overwrite"):
            preparer.prepare(self.source, self.destination)

    def test_every_manifest_file_corruption_rejected_before_output(self):
        manifest = json.loads((self.source / "final_manifest.json").read_bytes())
        for name in ["final_manifest.json", *manifest["files"]]:
            with self.subTest(name=name):
                path = self.source / name
                original = path.read_bytes()
                try:
                    path.write_bytes(original + b' ')
                    with self.assertRaises(ValueError):
                        preparer.prepare(self.source, self.destination)
                    self.assertFalse(self.destination.exists())
                finally:
                    path.write_bytes(original)

    def test_symlink_and_inside_source_rejected(self):
        path = self.source / "selected_model.joblib"
        original = path.read_bytes()
        path.unlink()
        target = self.root / "model"
        target.write_bytes(original)
        path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "Symlink forbidden"):
            preparer.prepare(self.source, self.destination)
        with self.assertRaisesRegex(ValueError, "inside experiment"):
            preparer.prepare(self.source, self.source / "web")
        self.assertFalse(self.destination.exists())


if __name__ == "__main__":
    unittest.main()
