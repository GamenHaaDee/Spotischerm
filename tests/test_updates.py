"""Bijwerken en terugzetten: wat er bewaard wordt, en dat je eigen bestanden nooit geraakt worden."""
import io
import zipfile

import pytest

import updates


@pytest.fixture
def app_dir(tmp_path):
    """Een geïnstalleerde app, met eigen bestanden die niet in de zip van GitHub zitten."""
    app = tmp_path / "spotify-scherm"
    (app / "app").mkdir(parents=True)
    (app / "app" / "spotischerm.py").write_text("versie 1.3")
    (app / "README.md").write_text("zelfde")
    (app / "install.sh").write_text("oud")
    (app / "config.env").write_text("SPOTIFY_CLIENT_ID=geheim")
    (app / ".spotify-cache").write_text("{}")
    return app


@pytest.fixture
def release(tmp_path):
    """De uitgepakte zip van de nieuwe versie."""
    root = tmp_path / "GamenHaaDee-Spotischerm-abc"
    (root / "app").mkdir(parents=True)
    (root / "app" / "spotischerm.py").write_text("versie 1.4")
    (root / "app" / "nieuw.py").write_text("nieuw bestand")
    (root / "README.md").write_text("zelfde")
    (root / "install.sh").write_text("oud")
    return root


def test_update_keeps_what_changes(app_dir, release, tmp_path):
    backup = tmp_path / "backup"
    updates.apply(release, app_dir, backup, "1.3")
    assert (app_dir / "app" / "spotischerm.py").read_text() == "versie 1.4"
    assert (app_dir / "app" / "nieuw.py").exists()
    assert (app_dir / "config.env").read_text() == "SPOTIFY_CLIENT_ID=geheim"  # eigen bestand blijft
    info = updates.previous(backup)
    assert info["versie"] == "1.3" and info["nieuw"] == ["app/nieuw.py"]
    kept = sorted(p.relative_to(backup / "bestanden").as_posix() for p in (backup / "bestanden").rglob("*") if p.is_file())
    assert kept == ["app/spotischerm.py"]  # alleen wat veranderde, niet README.md


def test_restore_puts_everything_back(app_dir, release, tmp_path):
    backup = tmp_path / "backup"
    updates.apply(release, app_dir, backup, "1.3")
    assert updates.restore(app_dir, backup) == "1.3"
    assert (app_dir / "app" / "spotischerm.py").read_text() == "versie 1.3"
    assert not (app_dir / "app" / "nieuw.py").exists()
    assert (app_dir / "config.env").read_text() == "SPOTIFY_CLIENT_ID=geheim"
    assert (app_dir / ".spotify-cache").exists()
    assert updates.previous(backup) is None  # opgeruimd
    with pytest.raises(ValueError):
        updates.restore(app_dir, backup)  # niets meer om terug te zetten


def test_failed_update_goes_back_by_itself(app_dir, release, tmp_path, monkeypatch):
    backup = tmp_path / "backup"
    real_copy = updates.shutil.copy2

    def broken_copy(src, dest):  # de schijf loopt vol halverwege het bijwerken
        if str(dest).endswith("nieuw.py"):
            raise OSError("No space left on device")
        return real_copy(src, dest)

    monkeypatch.setattr(updates.shutil, "copy2", broken_copy)
    with pytest.raises(OSError):
        updates.apply(release, app_dir, backup, "1.3")
    assert (app_dir / "app" / "spotischerm.py").read_text() == "versie 1.3"


def test_only_the_last_version_is_kept(app_dir, release, tmp_path):
    backup = tmp_path / "backup"
    updates.apply(release, app_dir, backup, "1.3")
    (release / "app" / "spotischerm.py").write_text("versie 1.5")
    updates.apply(release, app_dir, backup, "1.4")
    assert updates.previous(backup)["versie"] == "1.4"
    updates.restore(app_dir, backup)
    assert (app_dir / "app" / "spotischerm.py").read_text() == "versie 1.4"


def test_install_from_a_github_zip(app_dir, tmp_path, monkeypatch):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("GamenHaaDee-Spotischerm-abc/app/spotischerm.py", "versie 1.4")
        zf.writestr("GamenHaaDee-Spotischerm-abc/install.sh", "nieuw")

    class Reply:
        content = buf.getvalue()

    monkeypatch.setattr(updates, "APP_DIR", app_dir)
    monkeypatch.setattr(updates, "BACKUP_DIR", tmp_path / "backup")
    monkeypatch.setattr(updates.requests, "get", lambda url, **kw: Reply())
    u = updates.Updates.__new__(updates.Updates)  # zonder de thread die GitHub controleert
    u.current, u.latest = "1.3", {"version": "1.4", "name": "SpotiScherm 1.4", "zip": "https://example/zip"}
    ok, install_changed = u.install()
    assert ok and install_changed  # install.sh veranderd: dan vraagt het scherm om install.sh
    assert updates.previous(tmp_path / "backup")["versie"] == "1.3"
