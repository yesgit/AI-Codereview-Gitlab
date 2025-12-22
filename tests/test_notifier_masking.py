from biz.utils.im.feishu import FeishuNotifier


def test_mask_querystring():
    u = 'https://example.com/hook?token=abcd1234&foo=bar'
    masked = FeishuNotifier._mask_url(u)
    # token value must be masked
    assert 'abcd1234' not in masked
    assert '***' in masked


def test_mask_path_token():
    u = 'https://example.com/hooks/abcd1234'
    masked = FeishuNotifier._mask_url(u)
    assert 'abcd1234' not in masked
    assert '***' in masked
