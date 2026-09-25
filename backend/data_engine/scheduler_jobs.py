"""
数据采集调度器
基于 APScheduler 的定时任务管理
所有任务在后台自动运行，收盘后采集当日数据
"""
import logging
from datetime import datetime, time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from .collector import DataCollector
from .db import Database

logger = logging.getLogger(__name__)


class MarketScheduler:
    """市场数据采集调度器"""

    def __init__(self, db: Database = None):
        self.db = db or Database()
        self.collector = DataCollector(self.db)
        self.scheduler = BackgroundScheduler(
            timezone='Asia/Shanghai',
            job_defaults={
                'coalesce': True,          # 合并错过的任务
                'max_instances': 1,        # 每个任务最多1个实例
                'misfire_grace_time': 3600, # 错过1小时内仍可执行
            }
        )

    def setup_jobs(self):
        """配置所有定时任务"""

        # ===== A股任务 (收盘后 15:00) =====
        self.scheduler.add_job(
            self.collector.collect_a_stock_list,
            CronTrigger(day_of_week='mon-fri', hour=15, minute=5),
            id='a_stock_list', name='A股-股票列表', replace_existing=True
        )
        self.scheduler.add_job(
            self.collector.collect_a_daily_prices,
            CronTrigger(day_of_week='mon-fri', hour=15, minute=10),
            id='a_daily_prices', name='A股-日线行情', replace_existing=True
        )
        self.scheduler.add_job(
            self.collector.collect_a_valuation,
            CronTrigger(day_of_week='mon-fri', hour=15, minute=15),
            id='a_valuation', name='A股-估值数据', replace_existing=True
        )
        self.scheduler.add_job(
            self.collector.collect_a_fund_flow,
            CronTrigger(day_of_week='mon-fri', hour=15, minute=20),
            id='a_fund_flow', name='A股-北向资金', replace_existing=True
        )
        self.scheduler.add_job(
            self.collector.collect_a_market_breadth,
            CronTrigger(day_of_week='mon-fri', hour=15, minute=20),
            id='a_breadth', name='A股-市场情绪', replace_existing=True
        )

        # ===== 港股任务 (收盘后 16:30) =====
        self.scheduler.add_job(
            self.collector.collect_hk_stock_list,
            CronTrigger(day_of_week='mon-fri', hour=16, minute=35),
            id='hk_stock_list', name='港股-股票列表', replace_existing=True
        )
        self.scheduler.add_job(
            self.collector.collect_hk_daily_prices,
            CronTrigger(day_of_week='mon-fri', hour=16, minute=40),
            id='hk_daily_prices', name='港股-日线行情', replace_existing=True
        )

        # ===== 美股任务 (北京时间次日凌晨收盘后) =====
        # 美股夏令时: 北京时间 04:00 收盘, 冬令时: 05:00
        self.scheduler.add_job(
            self.collector.collect_us_stock_list,
            CronTrigger(day_of_week='tue-sat', hour=5, minute=30),
            id='us_stock_list', name='美股-股票列表', replace_existing=True
        )
        self.scheduler.add_job(
            self.collector.collect_us_daily_prices,
            CronTrigger(day_of_week='tue-sat', hour=5, minute=35),
            id='us_daily_prices', name='美股-日线行情', replace_existing=True
        )
        self.scheduler.add_job(
            self.collector.collect_vix,
            CronTrigger(day_of_week='tue-sat', hour=5, minute=40),
            id='vix', name='美股-VIX', replace_existing=True
        )

        # ===== 财务数据 (每周六凌晨) =====
        self.scheduler.add_job(
            self.collector.collect_a_financials,
            CronTrigger(day_of_week='sat', hour=2, minute=0),
            id='a_financials', name='A股-财务数据', replace_existing=True
        )

        # ===== 盘中情绪刷新 (可选, 每10分钟) =====
        self.scheduler.add_job(
            self.collector.collect_a_market_breadth,
            CronTrigger(day_of_week='mon-fri', hour='9-11,13-14', minute='*/10'),
            id='intraday_breadth', name='盘中-市场情绪', replace_existing=True
        )

        # 注册事件监听
        self.scheduler.add_listener(self._on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

        logger.info("所有定时任务配置完成")

    def _on_job_event(self, event):
        """任务执行事件处理"""
        if event.exception:
            logger.error(f"任务 [{event.job_id}] 执行失败: {event.exception}")
        else:
            logger.info(f"任务 [{event.job_id}] 执行成功")

    def start(self):
        """启动调度器"""
        self.setup_jobs()
        self.scheduler.start()
        logger.info("数据采集调度器已启动")

    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown(wait=False)
        logger.info("数据采集调度器已停止")

    def run_now(self, job_id: str = None):
        """立即执行某个/所有任务（用于手动触发）"""
        if job_id:
            job = self.scheduler.get_job(job_id)
            if job:
                job.func()
                logger.info(f"手动执行任务: {job_id}")
            else:
                logger.warning(f"任务不存在: {job_id}")
        else:
            logger.info("手动执行全量采集...")
            self.collector.collect_all()

    def get_status(self) -> dict:
        """获取调度器状态"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': str(job.next_run_time) if job.next_run_time else None,
            })
        return {
            'running': self.scheduler.running,
            'jobs': jobs,
        }
