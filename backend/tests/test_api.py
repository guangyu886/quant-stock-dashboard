"""
API 接口快速冒烟测试
验证所有端点正常响应
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

from api import app


@pytest.fixture(scope="module")
def client():
    """使用 lifespan 上下文管理器确保 db/scheduler 等初始化"""
    with TestClient(app) as c:
        yield c


class TestAPIEndpoints:

    def test_system_status(self, client):
        """系统状态端点"""
        response = client.get("/api/system/status")
        assert response.status_code == 200
        data = response.json()
        assert 'database' in data
        assert 'last_collect' in data

    def test_overview(self, client):
        """首页概览端点"""
        response = client.get("/api/overview")
        assert response.status_code == 200
        data = response.json()
        assert 'indices' in data
        assert 'updated' in data

    def test_sentiment_summary(self, client):
        """情绪评分端点"""
        response = client.get("/api/sentiment/summary")
        assert response.status_code == 200
        data = response.json()
        assert 'score' in data
        assert 0 <= data['score'] <= 100

    def test_valuation_rank(self, client):
        """估值排名端点"""
        response = client.get("/api/valuation/rank?market=A&metric=pe&limit=10")
        assert response.status_code in (200, 404)

    def test_valuation_distribution(self, client):
        """估值分布端点"""
        response = client.get("/api/valuation/distribution?market=A")
        assert response.status_code == 200

    def test_screener(self, client):
        """筛选端点"""
        response = client.get("/api/screener?pe_max=30&pb_max=5&roe_min=10&limit=20")
        assert response.status_code in (200, 404)

    def test_watchlist(self, client):
        """自选股 CRUD"""
        r = client.post("/api/watchlist/sh000001?note=test")
        assert r.status_code == 200
        r = client.get("/api/watchlist")
        assert r.status_code == 200
        r = client.delete("/api/watchlist/sh000001")
        assert r.status_code == 200

    def test_fund_flow(self, client):
        """北向资金"""
        response = client.get("/api/sentiment/fund-flow?days=5")
        assert response.status_code == 200

    def test_vix(self, client):
        """VIX"""
        response = client.get("/api/sentiment/vix?days=5")
        assert response.status_code == 200

    def test_breadth(self, client):
        """市场情绪"""
        response = client.get("/api/sentiment/breadth?market=A&days=5")
        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
