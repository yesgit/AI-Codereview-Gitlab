"""
日报路由模块
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, List
import fnmatch

from flask import Blueprint, jsonify

from biz.api import push_review_enabled
from biz.service.review_service import ReviewService
from biz.service.branch_webhook_service import BranchWebhookService
from biz.service.webhook_service import WebhookService
from biz.utils.im.dingtalk import DingTalkNotifier
from biz.utils.im.feishu import FeishuNotifier
from biz.utils.im.wecom import WeComNotifier
from biz.utils.im import notifier
from biz.utils.log import logger
from biz.utils.reporter import Reporter

daily_report_bp = Blueprint('daily_report', __name__)


def get_branch_for_log(log: dict) -> str:
    """从日志中获取分支名称"""
    if 'source_branch' in log and log['source_branch']:
        return log['source_branch']  # MR log
    elif 'branch' in log and log['branch']:
        return log['branch']  # Push log
    return None


def match_branch_config(log: dict, branch_configs: List[dict]) -> dict:
    """为单条日志匹配分支配置
    
    Args:
        log: 单条日志记录
        branch_configs: 该项目的所有分支配置
        
    Returns:
        匹配到的分支配置，如果没有匹配则返回 None
    """
    gitlab_base_url = log.get('gitlab_base_url')
    project_slug = log.get('project_slug')
    branch_name = get_branch_for_log(log)
    
    if not gitlab_base_url or not project_slug or not branch_name:
        return None
    
    # 先检查精确匹配
    for config in branch_configs:
        if config['branch_pattern'] == branch_name:
            logger.info(f"✅ 精确匹配分支配置: {gitlab_base_url}/{project_slug}:{branch_name}")
            return config
    
    # 再检查通配符匹配，按模式长度排序（最长优先）
    wildcard_configs = [
        config for config in branch_configs 
        if '*' in config['branch_pattern'] or '?' in config['branch_pattern']
    ]
    
    # 按模式长度降序排序（越长越具体）
    wildcard_configs.sort(key=lambda x: len(x['branch_pattern']), reverse=True)
    
    for config in wildcard_configs:
        if fnmatch.fnmatch(branch_name, config['branch_pattern']):
            logger.info(f"✅ 通配符匹配分支配置: {gitlab_base_url}/{project_slug}:{branch_name} -> {config['branch_pattern']}")
            return config
    
    return None


def send_report_to_config(logs: List[dict], config: dict, title_prefix: str = None):
    """根据配置发送报告
    
    Args:
        logs: 要发送的日志列表
        config: webhook 配置
        title_prefix: 报告标题前缀
    """
    if not logs:
        return
    
    # 检查是否启用日报
    if config and config.get('daily_report_enabled') is False:
        logger.info(f"⏭️ 跳过日报发送: {title_prefix} (daily_report_enabled=False)")
        return
    
    # 去重：基于 (author, message) 组合
    import pandas as pd
    df = pd.DataFrame(logs)
    df_unique = df.drop_duplicates(subset=["author", "commit_messages"])
    # 按照 author 排序
    df_sorted = df_unique.sort_values(by="author")
    # 转换为适合生成日报的格式
    commits = df_sorted.to_dict(orient="records")
    # 生成日报内容
    report_txt = Reporter().generate_report(json.dumps(commits), title_prefix=title_prefix)
    
    # 如果 config 为空，使用默认通知方式（环境变量）
    if not config or not any(config.get(f) for f in ['dingtalk_url', 'feishu_url', 'wecom_url']):
        # 使用默认通知方式
        notifier.send_notification(
            content=report_txt, 
            msg_type="markdown", 
            title=f"代码提交日报 - {title_prefix or '全部'}"
        )
        return
    
    # 发送通知到所有配置的IM平台
    if config.get('dingtalk_url'):
        dt_notifier = DingTalkNotifier(config=config)
        dt_notifier.send_message(
            content=report_txt, 
            msg_type="markdown", 
            title=f"代码提交日报 - {title_prefix or '全部'}"
        )
    if config.get('feishu_url'):
        fs_notifier = FeishuNotifier(config=config)
        fs_notifier.send_message(
            content=report_txt, 
            msg_type="markdown", 
            title=f"代码提交日报 - {title_prefix or '全部'}"
        )
    if config.get('wecom_url'):
        wc_notifier = WeComNotifier(config=config)
        wc_notifier.send_message(
            content=report_txt, 
            msg_type="markdown", 
            title=f"代码提交日报 - {title_prefix or '全部'}"
        )


def daily_report_task():
    """
    日报任务函数，供调度器调用
    """
    logger.info("=" * 80)
    logger.info("🚀 开始处理日报请求（调度或手动触发）")
    logger.info("=" * 80)
    
    # 获取当前日期0点和23点59分59秒的时间戳（使用 UTC 时间）
    start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    end_time = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=0).timestamp()
    
    logger.info(f"📋 时间范围: {datetime.fromtimestamp(start_time, tz=timezone.utc)} ~ {datetime.fromtimestamp(end_time, tz=timezone.utc)}")
    logger.info(f"📋 时间戳范围: {start_time} ~ {end_time}")
    logger.info(f"📋 Push Review 启用状态: {push_review_enabled}")

    try:
        # 获取当日所有审查日志
        if push_review_enabled:
            df = ReviewService().get_push_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)
        else:
            df = ReviewService().get_mr_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)

        if df.empty:
            logger.info("No data to process.")
            # 无数据时也发送通知，告知用户今日无审查记录
            message = f"""# 📋 代码提交日报 - 今日暂无提交

今日没有代码审查记录。
"""
            notifier.send_notification(
                content=message,
                msg_type="markdown",
                title="代码提交日报 - 今日暂无提交"
            )
            return

        # 转换为字典列表
        logs = df.to_dict(orient="records")
        
        # 按项目分组
        project_groups: Dict[str, List[dict]] = {}
        for log in logs:
            project_key = (log.get('gitlab_base_url'), log.get('project_slug'), log.get('project_name'))
            if project_key not in project_groups:
                project_groups[project_key] = []
            project_groups[project_key].append(log)
        
        logger.info(f"当日有 {len(logs)} 条记录，涉及 {len(project_groups)} 个项目")
        
        # 为每个项目处理报告
        for project_key, project_logs in project_groups.items():
            gitlab_base_url, project_slug, project_name = project_key
            
            # 获取该项目的所有分支配置
            branch_configs = BranchWebhookService.get_all_branch_webhooks(
                gitlab_base_url=gitlab_base_url,
                project_slug=project_slug
            )
            
            if branch_configs:
                # 有分支配置，按分支模式分组发送
                logger.info(f"项目 {project_name} 有 {len(branch_configs)} 个分支配置，按分支分组发送")
                
                # 为每条日志匹配分支配置
                branch_groups: Dict[str, List[dict]] = {}
                unmatched_logs = []
                
                for log in project_logs:
                    matched_config = match_branch_config(log, branch_configs)
                    if matched_config:
                        branch_pattern = matched_config['branch_pattern']
                        if branch_pattern not in branch_groups:
                            branch_groups[branch_pattern] = {'logs': [], 'config': matched_config}
                        branch_groups[branch_pattern]['logs'].append(log)
                    else:
                        unmatched_logs.append(log)
                
                # 为每个分支组发送报告
                for branch_pattern, group_data in branch_groups.items():
                    branch_logs = group_data['logs']
                    branch_config = group_data['config']
                    title_prefix = f"项目:{project_name} 分支:{branch_pattern}"
                    
                    # 检查分支配置的日报开关
                    if branch_config.get('daily_report_enabled') is False:
                        logger.info(f"⏭️ 跳过分支日报: {title_prefix} (daily_report_enabled=False), 共 {len(branch_logs)} 条记录")
                    else:
                        logger.info(f"发送分支日报: {title_prefix}, 共 {len(branch_logs)} 条记录")
                        send_report_to_config(branch_logs, branch_config, title_prefix=title_prefix)
                
                # 处理未匹配到分支配置的日志（发送到项目级配置或默认配置）
                if unmatched_logs:
                    logger.info(f"项目 {project_name} 有 {len(unmatched_logs)} 条日志未匹配到分支配置，尝试发送到项目级配置")
                    # 优先使用 gitlab_base_url + project_slug 查询项目配置
                    project_config = WebhookService.get_webhook_mapping_by_gitlab_project(
                        gitlab_base_url=gitlab_base_url,
                        project_slug=project_slug
                    )
                    # 如果没找到，回退到旧方式查询
                    if not project_config:
                        project_config = ReviewService().get_webhook_mapping(project_name=project_name)
                    # 检查项目配置是否有效（至少有一个 webhook URL）
                    if project_config and WebhookService.is_valid_webhook_config(project_config):
                        # 检查项目配置的日报开关
                        if project_config.get('daily_report_enabled') is False:
                            logger.info(f"⏭️ 跳过项目级日报: {project_name} (daily_report_enabled=False), 共 {len(unmatched_logs)} 条记录")
                        else:
                            logger.info(f"✅ 使用项目级配置发送: {gitlab_base_url}/{project_slug}")
                            send_report_to_config(unmatched_logs, project_config, title_prefix=f"项目:{project_name}")
                    else:
                        # 项目配置无效或不存在，发送到默认配置（系统级）
                        logger.info(f"⚠️ 项目配置无效，使用系统默认配置: {gitlab_base_url}/{project_slug}")
                        send_report_to_config(unmatched_logs, {}, title_prefix=f"项目:{project_name}")
            else:
                # 没有分支配置，按项目发送
                logger.info(f"项目 {project_name} 无分支配置，按项目发送")
                # 优先使用 gitlab_base_url + project_slug 查询项目配置
                project_config = WebhookService.get_webhook_mapping_by_gitlab_project(
                    gitlab_base_url=gitlab_base_url,
                    project_slug=project_slug
                )
                # 如果没找到，回退到旧方式查询
                if not project_config:
                    project_config = ReviewService().get_webhook_mapping(project_name=project_name)
                # 检查项目配置是否有效（至少有一个 webhook URL）
                if project_config and WebhookService.is_valid_webhook_config(project_config):
                    # 检查项目配置的日报开关
                    if project_config.get('daily_report_enabled') is False:
                        logger.info(f"⏭️ 跳过项目级日报: {project_name} (daily_report_enabled=False), 共 {len(project_logs)} 条记录")
                    else:
                        logger.info(f"✅ 使用项目级配置发送: {gitlab_base_url}/{project_slug}")
                        send_report_to_config(project_logs, project_config, title_prefix=f"项目:{project_name}")
                else:
                    # 项目配置无效或不存在，发送到默认配置（系统级）
                    logger.info(f"⚠️ 项目配置无效，使用系统默认配置: {gitlab_base_url}/{project_slug}")
                    send_report_to_config(project_logs, {}, title_prefix=f"项目:{project_name}")
        
        logger.info("日报任务执行完成")
        
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")


@daily_report_bp.route('/review/daily_report', methods=['GET'])
def daily_report():
    """
    日报路由处理函数
    """
    logger.info("=" * 80)
    logger.info("🚀 开始处理手动日报请求")
    logger.info("=" * 80)
    
    # 获取当前日期0点和23点59分59秒的时间戳（使用 UTC 时间）
    start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    end_time = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=0).timestamp()
    
    logger.info(f"📋 时间范围: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')} 到 {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')} (UTC)")
    logger.info(f"📋 时间戳范围: {start_time} 到 {end_time}")
    logger.info(f"📋 当前时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} (UTC)")
    logger.info(f"📋 当前本地时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📋 Push Review 启用状态: {push_review_enabled}")

    try:
        logger.info(f"🔍 开始查询审查日志...")
        # 获取当日所有审查日志
        if push_review_enabled:
            logger.info(f"🔍 查询 Push Review 日志")
            df = ReviewService().get_push_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)
        else:
            logger.info(f"🔍 查询 MR Review 日志")
            df = ReviewService().get_mr_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)

        logger.info(f"🔍 查询完成，共 {len(df)} 条记录")
        
        if df.empty:
            logger.info("⚠️ 没有数据，发送空数据响应")
            return jsonify({'message': 'No data to process.'}), 200
        
        logger.info(f"📊 数据预览（前5条）:")
        for idx, row in df.head().iterrows():
            logger.info(f"   - {row.get('project_name')}/{row.get('author')}: {row.get('commit_messages')[:50]}...")

        # 转换为字典列表
        logs = df.to_dict(orient="records")
        
        # 按项目分组
        project_groups: Dict[str, List[dict]] = {}
        for log in logs:
            project_key = (log.get('gitlab_base_url'), log.get('project_slug'), log.get('project_name'))
            if project_key not in project_groups:
                project_groups[project_key] = []
            project_groups[project_key].append(log)
        
        logger.info(f"当日有 {len(logs)} 条记录，涉及 {len(project_groups)} 个项目")
        
        # 为每个项目处理报告
        for project_key, project_logs in project_groups.items():
            gitlab_base_url, project_slug, project_name = project_key
            
            # 获取该项目的所有分支配置
            branch_configs = BranchWebhookService.get_all_branch_webhooks(
                gitlab_base_url=gitlab_base_url,
                project_slug=project_slug
            )
            
            if branch_configs:
                # 有分支配置，按分支模式分组发送
                logger.info(f"项目 {project_name} 有 {len(branch_configs)} 个分支配置，按分支分组发送")
                
                # 为每条日志匹配分支配置
                branch_groups: Dict[str, List[dict]] = {}
                unmatched_logs = []
                
                for log in project_logs:
                    matched_config = match_branch_config(log, branch_configs)
                    if matched_config:
                        branch_pattern = matched_config['branch_pattern']
                        if branch_pattern not in branch_groups:
                            branch_groups[branch_pattern] = {'logs': [], 'config': matched_config}
                        branch_groups[branch_pattern]['logs'].append(log)
                    else:
                        unmatched_logs.append(log)
                
                # 为每个分支组发送报告
                for branch_pattern, group_data in branch_groups.items():
                    branch_logs = group_data['logs']
                    branch_config = group_data['config']
                    title_prefix = f"项目:{project_name} 分支:{branch_pattern}"
                    logger.info(f"发送分支日报: {title_prefix}, 共 {len(branch_logs)} 条记录")
                    send_report_to_config(branch_logs, branch_config, title_prefix=title_prefix)
                
                # 处理未匹配到分支配置的日志（发送到项目级配置或默认配置）
                if unmatched_logs:
                    logger.info(f"项目 {project_name} 有 {len(unmatched_logs)} 条日志未匹配到分支配置，尝试发送到项目级配置")
                    # 优先使用 gitlab_base_url + project_slug 查询项目配置
                    project_config = WebhookService.get_webhook_mapping_by_gitlab_project(
                        gitlab_base_url=gitlab_base_url,
                        project_slug=project_slug
                    )
                    # 如果没找到，回退到旧方式查询
                    if not project_config:
                        project_config = ReviewService().get_webhook_mapping(project_name=project_name)
                    # 检查项目配置是否有效（至少有一个 webhook URL）
                    if project_config and WebhookService.is_valid_webhook_config(project_config):
                        logger.info(f"✅ 使用项目级配置发送: {gitlab_base_url}/{project_slug}")
                        send_report_to_config(unmatched_logs, project_config, title_prefix=f"项目:{project_name}")
                    else:
                        # 项目配置无效或不存在，发送到默认配置（系统级）
                        logger.info(f"⚠️ 项目配置无效，使用系统默认配置: {gitlab_base_url}/{project_slug}")
                        send_report_to_config(unmatched_logs, {}, title_prefix=f"项目:{project_name}")
            else:
                # 没有分支配置，按项目发送
                logger.info(f"项目 {project_name} 无分支配置，按项目发送")
                # 优先使用 gitlab_base_url + project_slug 查询项目配置
                project_config = WebhookService.get_webhook_mapping_by_gitlab_project(
                    gitlab_base_url=gitlab_base_url,
                    project_slug=project_slug
                )
                # 如果没找到，回退到旧方式查询
                if not project_config:
                    project_config = ReviewService().get_webhook_mapping(project_name=project_name)
                # 检查项目配置是否有效（至少有一个 webhook URL）
                if project_config and WebhookService.is_valid_webhook_config(project_config):
                    logger.info(f"✅ 使用项目级配置发送: {gitlab_base_url}/{project_slug}")
                    send_report_to_config(project_logs, project_config, title_prefix=f"项目:{project_name}")
                else:
                    # 项目配置无效或不存在，发送到默认配置（系统级）
                    logger.info(f"⚠️ 项目配置无效，使用系统默认配置: {gitlab_base_url}/{project_slug}")
                    send_report_to_config(project_logs, {}, title_prefix=f"项目:{project_name}")

        # 返回成功信息
        return jsonify({'message': 'Daily report generated and sent successfully.'}), 200
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        return jsonify({'message': f"Failed to generate daily report: {e}"}), 500
