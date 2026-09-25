<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
    <!-- 侧边栏 -->
    <aside class="fixed left-0 top-0 h-full w-56 bg-slate-900/80 backdrop-blur-xl border-r border-slate-800 z-40 flex flex-col">
      <div class="p-5 border-b border-slate-800">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center text-white font-bold text-sm">Q</div>
          <div>
            <div class="text-sm font-bold text-white">量化投研</div>
            <div class="text-xs text-slate-500">Stock Dashboard</div>
          </div>
        </div>
      </div>
      <nav class="flex-1 p-3 space-y-1">
        <router-link v-for="item in navItems" :key="item.path" :to="item.path"
          class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200"
          :class="$route.path === item.path ? 'bg-blue-600/20 text-blue-400 font-medium border border-blue-500/20' : 'text-slate-400 hover:text-white hover:bg-slate-800/50'"
        >
          <span class="text-lg">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="p-3 border-t border-slate-800">
        <div class="flex items-center gap-2 text-xs text-slate-500">
          <span :class="statusDot"></span>
          {{ statusText }}
        </div>
        <button @click="refreshData" class="mt-2 w-full py-1.5 text-xs bg-slate-800 hover:bg-slate-700 rounded text-slate-400 transition-colors">
          🔄 刷新数据
        </button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="ml-56 min-h-screen">
      <header class="sticky top-0 z-30 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800 px-6 py-3">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-bold text-white">{{ currentTitle }}</h2>
            <p class="text-xs text-slate-500">{{ currentDesc }}</p>
          </div>
          <div class="flex items-center gap-4 text-xs text-slate-500">
            <span>📅 {{ today }}</span>
            <span>🕐 {{ time }}</span>
          </div>
        </div>
      </header>
      <div class="p-6">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { triggerCollect } from './api'

const route = useRoute()
const statusText = ref('✅ 就绪')
const statusDot = ref('w-2 h-2 rounded-full bg-green-400')
const today = ref('')
const time = ref('')

const navItems = [
  { path: '/', label: '行情总览', icon: '📈', desc: '三大市场指数·涨跌统计·北向资金·VIX' },
  { path: '/valuation', label: '估值分析', icon: '📊', desc: 'PE/PB排名·估值分布·历史分位' },
  { path: '/technical', label: '技术指标', icon: '🕯️', desc: 'K线图·30+指标·信号检测' },
  { path: '/sentiment', label: '市场情绪', icon: '🎯', desc: '北向资金趋势·涨跌比·VIX指数' },
  { path: '/screener', label: '基本面筛选', icon: '🔍', desc: 'PE/PB/ROE/增长率组合筛选' },
  { path: '/watchlist', label: '自选股', icon: '⭐', desc: '管理自选股·持仓跟踪·估值概览' },
]

const currentTitle = computed(() => {
  const item = navItems.find(n => n.path === route.path)
  return item ? item.label : '行情总览'
})
const currentDesc = computed(() => {
  const item = navItems.find(n => n.path === route.path)
  return item ? item.desc : ''
})

function updateTime() {
  const now = new Date()
  today.value = now.toLocaleDateString('zh-CN')
  time.value = now.toLocaleTimeString('zh-CN')
}

const refreshData = async () => {
  statusText.value = '刷新中...'
  statusDot.value = 'w-2 h-2 rounded-full bg-yellow-400 animate-pulse'
  try { await triggerCollect(); statusText.value = '✅ 就绪'; statusDot.value = 'w-2 h-2 rounded-full bg-green-400' }
  catch { statusText.value = '⚠️ 失败'; statusDot.value = 'w-2 h-2 rounded-full bg-red-400' }
}

onMounted(() => { updateTime(); setInterval(updateTime, 1000) })
</script>
