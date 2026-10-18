"""Regression tests for the existing-stack deploy path, without a Docker daemon."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("deploy", Path(__file__).resolve().parents[1] / "scripts/deploy_existing_frontend.py")
deploy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy)
CONF = '''server {
    listen 80;
    root /srv/frontend;
    location /api/ { proxy_pass http://app:8000; }
    location /assets/ { try_files $uri =404; }
    location / { try_files $uri @frontend; }
    location @frontend { proxy_pass http://app:8000; }
}
'''


class DeploymentTests(unittest.TestCase):
    def test_only_homepage_route_added_and_redeploy_replaces_marker(self):
        first = deploy.configuration(CONF, "first")
        second = deploy.configuration(first, "second")
        self.assertNotIn("/first/", second)
        self.assertEqual(second.count("location = / {"), 1)
        for route in ["location /api/", "location /assets/", "location @frontend"]:
            original = next(line for line in CONF.splitlines() if route in line)
            self.assertIn(original, second)

    def test_unknown_layout_and_exact_root_fail_before_changes(self):
        for text in [CONF.replace("/srv/frontend", "/other"), CONF + "server {\n}\n",
                     CONF.replace("location / {", "location = / {")]:
            with self.assertRaises(RuntimeError):
                deploy.configuration(text, "release")

    def test_assets_namespaced_login_same_origin_and_strict_csp(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            (source / "index.html").write_text('''<script>window.x=1</script><img onerror="alert(1)" src="./assets/image.webp"><script src="./app.js"></script><a href="#news">News</a><a href="http://192.168.100.50:8188">Login</a>''')
            (source / "app.js").write_text("const src='./assets/pic.webp';const rt=`./rt.html?rt=${rt}`;")
            destination = Path(tmp) / "release"
            deploy.prepare_site(source, destination, "test")
            html = (destination / "index.html").read_text()
            self.assertNotIn("onerror", html)
            self.assertNotIn("<script>", html)
            self.assertIn('href="/login"', html)
            self.assertIn('href="#news"', html)
            self.assertIn('/_rw10_ui/test/assets/image.webp', html)
            self.assertIn('/_rw10_ui/test/app.js', html)
            self.assertTrue((destination / "index-inline-1.js").exists())
            self.assertIn("window.location.origin + '/login'", (destination / "config.js").read_text())

    def test_failed_validation_restores_bind_inode_and_reloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            conf = Path(tmp) / "default.conf"
            conf.write_text(CONF)
            inode = conf.stat().st_ino
            calls = []
            def command(*args):
                calls.append(args)
                return ""
            def fail():
                raise RuntimeError("HTTP verification failed")
            with patch.object(deploy, "run", command):
                with self.assertRaisesRegex(RuntimeError, "HTTP verification failed"):
                    deploy.activate(conf, deploy.configuration(CONF, "release"), CONF, fail)
            self.assertEqual(conf.read_text(), CONF)
            self.assertEqual(conf.stat().st_ino, inode)
            self.assertEqual(sum(call[-1] == "reload" for call in calls), 2)
            self.assertFalse(any("stop" in call or "compose" in call for call in calls))

    def test_nginx_syntax_failure_restores_without_loading_bad_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            conf = Path(tmp) / "default.conf"
            conf.write_text(CONF)
            calls = []
            def command(*args):
                calls.append(args)
                if len(calls) == 1:
                    raise RuntimeError("bad nginx config")
                return ""
            with patch.object(deploy, "run", command):
                with self.assertRaisesRegex(RuntimeError, "bad nginx config"):
                    deploy.activate(conf, "bad", CONF, lambda: None)
            self.assertEqual(conf.read_text(), CONF)
            self.assertEqual(sum(call[-1] == "reload" for call in calls), 1)

    def test_verification_detects_old_app_asset_regression(self):
        before = {"/assets/product.js": (200, b"old app", "application/javascript")}
        def http(path):
            if path == "/":
                return 200, b'/_rw10_ui/test/editorial-v6.css', "text/html"
            return 200, b"different", "text/plain"
        with patch.object(deploy, "response", http):
            with self.assertRaisesRegex(RuntimeError, "asset changed"):
                deploy.verify("test", before)


if __name__ == "__main__":
    unittest.main()
