import os
from biz.utils.db import get_engine
from biz.service.webhook_service import WebhookService


def setup_module():
    # Use in-memory sqlite for tests
    os.environ['DB_DRIVER'] = 'sqlite'
    os.environ['DB_FILE'] = ':memory:'
    # Clear cached engine so tests create a fresh in-memory engine
    try:
        get_engine.cache_clear()
    except Exception:
        pass
    WebhookService.init_db()


def test_create_and_get_mapping():
    WebhookService.create_or_update_webhook_mapping(project_name='proj1', url_slug='default', feishu_url='https://example.com/hook1')
    m = WebhookService.get_webhook_mapping(project_name='proj1', url_slug='default')
    assert m is not None
    assert m['project_name'] == 'proj1'
    assert m['feishu_url'] == 'https://example.com/hook1'


def test_update_mapping():
    WebhookService.create_or_update_webhook_mapping(project_name='proj1', url_slug='default', feishu_url='https://example.com/hook2')
    m2 = WebhookService.get_webhook_mapping(project_name='proj1', url_slug='default')
    assert m2 is not None
    assert m2['feishu_url'] == 'https://example.com/hook2'


def test_get_all_and_delete():
    WebhookService.create_or_update_webhook_mapping(project_name='proj2', url_slug='alt', dingtalk_url='https://d.example/hook')
    allm = WebhookService.get_all_webhook_mappings()
    # Ensure there are at least two entries (proj1 and proj2)
    assert len(allm) >= 2
    pid = None
    for r in allm:
        if r.get('project_name') == 'proj2':
            pid = r.get('id')
            break
    assert pid is not None
    WebhookService.delete_webhook_mapping(pid)
    m = WebhookService.get_webhook_mapping(project_name='proj2', url_slug='alt')
    assert m is None
