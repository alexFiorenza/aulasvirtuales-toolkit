"""Global test fixtures for aulasvirtuales-toolkit."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest


# ---------------------------------------------------------------------------
# Moodle HTML / JSON fixtures
# ---------------------------------------------------------------------------

SESSKEY = "abc123sesskey"

DASHBOARD_HTML = f"""
<html><body>
<script>M.cfg = {{"sesskey":"{SESSKEY}","wwwroot":"https://aulasvirtuales.frba.utn.edu.ar"}};</script>
</body></html>
"""

SAMPLE_COURSES_RESPONSE = [
    {
        "error": False,
        "data": {
            "courses": [
                {"id": 101, "fullname": "Matemática Discreta", "viewurl": "https://aulasvirtuales.frba.utn.edu.ar/course/view.php?id=101"},
                {"id": 202, "fullname": "Sistemas Operativos", "viewurl": "https://aulasvirtuales.frba.utn.edu.ar/course/view.php?id=202"},
            ]
        },
    }
]

SAMPLE_COURSE_STATE = {
    "cm": [
        {"id": 1, "name": "Apunte Tema 1", "module": "resource", "sectionid": "10", "uservisible": True, "url": "/mod/resource/view.php?id=1"},
        {"id": 2, "name": "Foro General", "module": "forum", "sectionid": "10", "uservisible": True, "url": "/mod/forum/view.php?id=2"},
        {"id": 3, "name": "Recurso Oculto", "module": "resource", "sectionid": "10", "uservisible": False, "url": None},
        {"id": 4, "name": "Carpeta PDFs", "module": "folder", "sectionid": "20", "uservisible": True, "url": "/mod/folder/view.php?id=4"},
        {"id": 5, "name": "Aviso importante", "module": "label", "sectionid": "10", "uservisible": True, "url": None, "description": "<p>Leer antes del parcial.</p>"},
        {"id": 6, "name": "Reglamento", "module": "page", "sectionid": "10", "uservisible": True, "url": "/mod/page/view.php?id=6", "description": None},
        {"id": 7, "name": "Campus Virtual", "module": "url", "sectionid": "10", "uservisible": True, "url": "/mod/url/view.php?id=7", "description": None},
    ],
    "section": [
        {"id": "10", "number": 1, "title": "Unidad 1", "visible": True},
        {"id": "20", "number": 2, "title": "Unidad 2", "visible": True},
        {"id": "30", "number": 3, "title": "Unidad Oculta", "visible": False},
    ],
}

SAMPLE_URL_VIEW_HTML = """
<html><body>
<div class="urlworkaround">
  <a href="https://meet.google.com/abc-def-ghi">Continuar al enlace</a>
</div>
</body></html>
"""

SAMPLE_URL_META_REFRESH_HTML = """
<html><head>
<meta http-equiv="refresh" content="3; url=https://zoom.us/j/123456789">
</head><body></body></html>
"""

SAMPLE_PAGE_VIEW_HTML = """
<html><body>
<div class="box py-3 generalbox">
  <p>Este es el contenido de la página.</p>
  <p>Con varios párrafos.</p>
</div>
</body></html>
"""

SAMPLE_FORUM_DISCUSSIONS_HTML = """
<html><body>
<a href="discuss.php?d=100">Bienvenidos al foro</a>
<a href="discuss.php?d=100">Bienvenidos al foro</a>
<a href="discuss.php?d=200">Consulta sobre TP1</a>
<a href="discuss.php?d=300">Dudas parcial</a>
</body></html>
"""

SAMPLE_POSTS_RESPONSE = [
    {
        "error": False,
        "data": {
            "posts": [
                {"id": 1, "subject": "Bienvenidos", "author": {"fullname": "Prof. García"}, "message": "<p>Hola a todos!</p>", "timecreated": 1700000000},
                {"id": 2, "subject": "Re: Bienvenidos", "author": {"fullname": "Juan Pérez"}, "message": "<p>Gracias profe</p>", "timecreated": 1700001000},
            ]
        },
    }
]

SAMPLE_EVENTS_RESPONSE = [
    {
        "error": False,
        "data": {
            "events": [
                {
                    "id": 1,
                    "name": "Entrega TP1",
                    "course": {"fullname": "Matemática Discreta"},
                    "modulename": "assign",
                    "timesort": 1700100000,
                    "url": "https://aulasvirtuales.frba.utn.edu.ar/mod/assign/view.php?id=1",
                    "action": {"name": "Entregar"},
                },
            ]
        },
    }
]

SAMPLE_GRADES_HTML = """
<html><body>
<table class="user-grade">
<tr><th>Ítem de calificación</th><th></th><th>Calificación</th><th>Rango</th><th>Porcentaje</th><th>Retroalimentación</th></tr>
<tr><td>Parcial 1</td><td></td><td>8.00</td><td>0–10</td><td>80.00 %</td><td>Bien</td></tr>
<tr><td>TP1</td><td></td><td>10.00</td><td>0–10</td><td>100.00 %</td><td>Excelente</td></tr>
</table>
</body></html>
"""

SAMPLE_GRADES_EMPTY_HTML = """
<html><body>
<div>No grades available</div>
</body></html>
"""

SAMPLE_GRADES_ACTION_MENU_HTML = """
<html><body>
<table class="table generaltable user-grade">
<thead><tr>
<th colspan="2">Ítem de calificación</th>
<th>Ponderación calculada</th>
<th>Calificación</th>
<th>Rango</th>
<th>Porcentaje</th>
<th>Retroalimentación</th>
<th>Aporta al total del curso</th>
</tr></thead>
<tbody>
<tr><th colspan="8">Curso Total</th></tr>
<tr><td rowspan="4"></td></tr>
<tr>
<th><a class="gradeitemheader" href="/mod/assign/view.php?id=100">TPG1 Ética</a></th>
<td>-</td>
<td><div class="d-flex"><div>Entrega Muy bien</div><div><div class="action-menu moodle-actionmenu"><a title="Acciones">...</a></div></div></div></td>
<td>No entrega–Entrega Muy bien</td>
<td>75,00 %</td>
<td>&nbsp;</td>
<td>-</td>
</tr>
<tr>
<th><a class="gradeitemheader" href="/mod/quiz/view.php?id=200">Quiz 1</a></th>
<td>-</td>
<td><div class="d-flex"><div>8,50</div><div><div class="action-menu moodle-actionmenu"><a title="Acciones">...</a></div></div></div></td>
<td>0–10</td>
<td>85,00 %</td>
<td>&nbsp;</td>
<td>-</td>
</tr>
<tr>
<th><a class="gradeitemheader" href="/mod/assign/view.php?id=300">TPG2</a></th>
<td>-</td>
<td><div class="d-flex"><div></div><div><div class="action-menu moodle-actionmenu"><a title="Acciones">...</a></div></div></div></td>
<td>–</td>
<td></td>
<td>&nbsp;</td>
<td>-</td>
</tr>
</tbody>
</table>
</body></html>
"""

SAMPLE_RESOURCE_HTML = """
<html><body>
<a href="https://aulasvirtuales.frba.utn.edu.ar/pluginfile.php/12345/mod_resource/content/1/apunte.pdf">Download</a>
</body></html>
"""

SAMPLE_FOLDER_HTML = """
<html><body>
<a href="https://aulasvirtuales.frba.utn.edu.ar/pluginfile.php/12345/mod_folder/content/1/archivo1.pdf">archivo1.pdf</a>
<a href="https://aulasvirtuales.frba.utn.edu.ar/pluginfile.php/12345/mod_folder/content/1/archivo2.pdf">archivo2.pdf</a>
</body></html>
"""

SAMPLE_ASSIGNMENT_HTML = """
<html><body>
<table>
<tr><th>Estado de la entrega</th><td class="submissionstatussubmitted">Enviado para calificar</td></tr>
<tr><th>Calificación</th><td>8.50</td></tr>
</table>
<script>
M.core_comment.init(Y, {"client_id":"abc","itemid":123,"commentarea":"submission_comments","courseid":101,"contextid":456,"component":"assignsubmission_comments"});
</script>
</body></html>
"""

SAMPLE_COMMENTS_RESPONSE = {
    "list": [
        {"fullname": "Prof. García", "time": "10/11/2024", "content": "<p>Buen trabajo</p>"},
    ]
}


# ---------------------------------------------------------------------------
# Shared pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_config_dir(tmp_path, monkeypatch):
    """Redirect config to a temp directory."""
    config_dir = tmp_path / ".config" / "aulasvirtuales"
    config_dir.mkdir(parents=True)
    monkeypatch.setattr("aulasvirtuales.config.CONFIG_DIR", config_dir)
    monkeypatch.setattr("aulasvirtuales.config.CONFIG_FILE", config_dir / "config.json")
    return config_dir


@pytest.fixture
def tmp_download_dir(tmp_path, monkeypatch):
    """Redirect download directory to a temp directory."""
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    monkeypatch.setattr("aulasvirtuales.config.DEFAULT_DOWNLOAD_DIR", download_dir)
    return download_dir


@pytest.fixture
def mock_keyring(monkeypatch):
    """Mock the keyring module to use an in-memory store."""
    store = {}

    def _set_password(service, key, value):
        store[(service, key)] = value

    def _get_password(service, key):
        return store.get((service, key))

    def _delete_password(service, key):
        if (service, key) in store:
            del store[(service, key)]
        else:
            import keyring.errors
            raise keyring.errors.PasswordDeleteError()

    monkeypatch.setattr("keyring.set_password", _set_password)
    monkeypatch.setattr("keyring.get_password", _get_password)
    monkeypatch.setattr("keyring.delete_password", _delete_password)
    return store


@pytest.fixture
def mock_http_client():
    """Create a mock httpx.Client with common response patterns."""
    client = MagicMock(spec=httpx.Client)
    return client
