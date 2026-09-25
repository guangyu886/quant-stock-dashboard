import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Valuation from '../views/Valuation.vue'
import Technical from '../views/Technical.vue'
import Sentiment from '../views/Sentiment.vue'
import Screener from '../views/Screener.vue'
import Watchlist from '../views/Watchlist.vue'

const routes = [
  { path: '/', name: 'Home', component: Home, meta: { title: '行情总览' } },
  { path: '/valuation', name: 'Valuation', component: Valuation, meta: { title: '估值分析' } },
  { path: '/technical', name: 'Technical', component: Technical, meta: { title: '技术指标' } },
  { path: '/sentiment', name: 'Sentiment', component: Sentiment, meta: { title: '市场情绪' } },
  { path: '/screener', name: 'Screener', component: Screener, meta: { title: '基本面筛选' } },
  { path: '/watchlist', name: 'Watchlist', component: Watchlist, meta: { title: '自选股' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
