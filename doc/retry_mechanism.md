# 任务重试机制说明

## 概述

系统支持在代码审查任务失败时自动重试,特别是针对网络超时、API 限流等暂时性错误。

## 配置项

在 `.env` 文件中添加以下配置:

```bash
# 任务重试配置
MAX_RETRIES=3              # 最大重试次数 (默认: 3)
RETRY_DELAY_SECONDS=60     # 每次重试的延迟秒数 (默认: 60)
```

## 支持的队列模式

重试机制支持两种队列模式:

### 1. Multiprocessing 模式 (默认)
- 使用多进程处理任务
- 失败时在新线程中延迟后重新启动进程
- 适用于单机部署

### 2. RQ (Redis Queue) 模式
- 使用 Redis 作为任务队列
- 支持任务持久化,服务重启不丢失任务
- 适用于分布式部署
- 配置方法:
  ```bash
  QUEUE_DRIVER=rq
  REDIS_URL=redis://redis:6379
  WORKER_QUEUE=default
  ```

## 可重试的异常类型

以下类型的异常会自动触发重试:

### OpenAI 相关异常
- `openai.APITimeoutError` - 请求超时
- `openai.APIConnectionError` - 连接错误
- `openai.RateLimitError` - API 限流

### HTTP 相关异常
- `httpx.TimeoutException` - HTTP 超时
- `httpx.ConnectTimeout` - 连接超时
- `httpx.ReadTimeout` - 读取超时

### 其他异常
- `ConnectionError` - 网络连接错误
- `TimeoutError` - 通用超时错误

### 基于异常消息的判断
异常消息中包含以下关键词也会触发重试:
- `timeout`
- `connection`
- `rate limit`
- `temporarily unavailable`

## 重试流程

```
Webhook 触发 → 队列处理 → 执行审查
                    ↓
                 失败?
                    ↓
              可重试异常?
                    ↓
          重试次数 < MAX_RETRIES?
                    ↓
            [重新入队，延迟 RETRY_DELAY_SECONDS 秒]
                    ↓
              稍后自动重试
                    ↓
           达到最大重试次数?
                    ↓
        [发送失败通知, 不再重试]
```

## 日志示例

### 成功重试
```
2025-12-24 10:00:00,000 - WARNING - 任务失败 (第 1/3 次重试): APITimeoutError: Request timed out.
2025-12-24 10:00:00,001 - INFO - 将在 60 秒后重试...
2025-12-24 10:01:00,000 - INFO - Task scheduled for retry in 60s using multiprocessing
2025-12-24 10:01:00,001 - INFO - Retry task started in new process after 60s: 12345
```

### 达到最大重试次数
```
2025-12-24 10:05:00,000 - WARNING - 任务失败 (第 3/3 次重试): APITimeoutError: Request timed out.
2025-12-24 10:05:00,001 - ERROR - 已达到最大重试次数 3，放弃重试
```

## 适用场景

重试机制特别适用于以下场景:

1. **网络波动** - 短暂的网络延迟或不稳定
2. **API 限流** - OpenAI 或其他 API 服务临时限流
3. **服务繁忙** - AI 服务暂时响应缓慢
4. **连接超时** - 建立连接时间过长

## 注意事项

1. **重试成本** - 每次重试都会调用 AI API,可能产生额外费用
2. **延迟通知** - 重试期间不会发送失败通知,只有达到最大重试次数才会通知
3. **队列持久性** - Multiprocessing 模式下服务重启会丢失队列中的任务
4. **配置合理** - 根据实际场景调整 `MAX_RETRIES` 和 `RETRY_DELAY_SECONDS`

## 监控建议

1. 监控日志中的重试次数,判断是否需要调整配置
2. 关注重试失败的通知,排查根本原因
3. 如果频繁触发重试,考虑:
   - 增加 `RETRY_DELAY_SECONDS`
   - 减少 `MAX_RETRIES`
   - 检查网络连接
   - 联系 AI 服务提供商

## 故障排查

### 问题: 任务一直重试不成功
**可能原因:**
- API 密钥失效或额度不足
- 网络配置问题
- AI 服务宕机

**解决方案:**
1. 检查 API 密钥配置
2. 测试网络连接
3. 查看 AI 服务状态页面
4. 调低 `MAX_RETRIES` 避免无限重试

### 问题: 重试延迟太长
**解决方案:**
- 减少 `RETRY_DELAY_SECONDS` 的值
- 建议值: 30-120 秒之间

### 问题: 达到最大重试次数仍失败
**解决方案:**
- 增加网络稳定性
- 检查 AI 服务可用性
- 考虑使用其他 AI 服务提供商作为备份
