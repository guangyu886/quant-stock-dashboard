<template>
  <div class="space-y-6">
    <!-- 加载/错误状态 -->
    <div v-if="loading" class="text-center py-20">
      <div class="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-3"></div>
      <p class="text-slate-500">正在加载行情数据...</p>
    </div>
    <div v-else-if="error" class="text-center py-20">
      <p class="text-rose-400 mb-2">⚠️ 数据加载失败</p>
      <p class="text-slate-500 text-sm mb-4">{{ error }}</p>
      <button @click="loadData" class="px-4 py-2 bg-blue-600 rounded-lg text-white text-sm hover:bg-blue-700">重试</button>
    </div>
    <!-- 指数卡片 -->
    <div v-else class="space-y-6">
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <div v-for="(val, name) in overview.indices" :key="name"
        class="bg-slate-900/60 backdrop-blur rounded-xl p-4 border border-slate-800/60 hover:border-slate-700/60 transition-all duration-300">
        <div class="text-xs text-slate-500 truncate">{{ name }}</div>
        <div class="text-lg font-bold mt-1.5 text-white tracking-tight">{{ formatNum(val.close) }}</div>
        <div :class="val.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'" class="text-sm mt-0.5 font-medium">
          {{ val.change_pct >= 0 ? '+' : '' }}{{ formatPct(val.change_pct) }}%
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <!-- 情绪评分 -->
      <div class="bg-slate-900/60 backdrop-blur rounded-xl p-5 border border-slate-800/60">
        <h3 class="text-sm font-medium text-slate-400 mb-4">市场情绪指数</h3>
        <div class="flex items-end gap-4">
          <div class="text-6xl font-bold tracking-tight" :class="sentimentColor">{{ sentiment?.score || 50 }}</div>
          <div class="text-lg text-slate-400 pb-1">{{ sentiment?.level || '中性' }}</div>
        </div>
        <div class="w-full bg-slate-800 rounded-full h-1.5 mt-4">
          <div class="h-1.5 rounded-full transition-all duration-700" :style="{ width: (sentiment?.score || 50) + '%' }"
            :class="sentimentBarColor"></div>
        </div>
      </div>

      <!-- 涨跌统计 -->
      <div class="bg-slate-900/60 backdrop-blur rounded-xl p-5 border border-slate-800/60">
        <h3 class="text-sm font-medium text-slate-400 mb-4">今日市场</h3>
        <div class="grid grid-cols-2 gap-3">
          <div class="bg-slate-800/40 rounded-lg p-3">
            <div class="text-xs text-slate-500">上涨</div>
            <div class="text-xl font-bold text-emerald-400">{{ overview.market_breadth?.up || 0 }}</div>
          </div>
          <div class="bg-slate-800/40 rounded-lg p-3">
            <div class="text-xs text-slate-500">下跌</div>
            <div class="text-xl font-bold text-rose-400">{{ overview.market_breadth?.down || 0 }}</div>
          </div>
          <div class="bg-slate-800/40 rounded-lg p-3">
            <div class="text-xs text-slate-500">涨停</div>
            <div class="text-xl font-bold text-amber-400">{{ overview.market_breadth?.limit_up || 0 }}</div>
          </div>
          <div class="bg-slate-800/40 rounded-lg p-3">
            <div class="text-xs text-slate-500">成交额(亿)</div>
            <div class="text-xl font-bold text-slate-200">{{ overview.market_breadth?.total_volume || 0 }}</div>
          </div>
        </div>
      </div>

      <!-- 北向+VIX -->
      <div class="bg-slate-900/60 backdrop-blur rounded-xl p-5 border border-slate-800/60">
        <h3 class="text-sm font-medium text-slate-400 mb-4">资金 & 恐慌</h3>
        <div class="space-y-4">
          <div>
            <div class="text-xs text-slate-500 mb-1">北向资金净流入</div>
            <div class="text-2xl font-bold" :class="(overview.north_flow?.net_flow || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'">
              {{ overview.north_flow?.net_flow || '-' }} <span class="text-sm font-normal text-slate-500">亿</span>
            </div>
          </div>
          <div class="border-t border-slate-800 pt-3">
            <div class="text-xs text-slate-500 mb-1">VIX 恐慌指数</div>
            <div class="text-2xl font-bold" :class="(overview.vix?.close || 0) > 25 ? 'text-rose-400' : 'text-cyan-400'">
              {{ overview.vix?.close || '-' }}
            </div>
          </div>
        </div>
      </div>
    </div>
    </div><!-- end v-else -->
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { getOverview, getSentimentSummary } from '../api'

const overview = ref({ indices: {}, market_breadth: {}, north_flow: {}, vix: {} })
const sentiment = ref(null)
const loading = ref(true)
const error = ref(null)

const sentimentColor = computed(() => {
  if (!sentiment.value) return 'text-slate-400'
  const s = sentiment.value.score
  if (s >= 75) return 'text-rose-400'; if (s >= 60) return 'text-amber-400'
  if (s >= 40) return 'text-cyan-400'; if (s >= 25) return 'text-yellow-500'
  return 'text-emerald-400'
})
const sentimentBarColor = computed(() => {
  if (!sentiment.value) return 'bg-slate-500'
  const s = sentiment.value.score
  return s >= 60 ? 'bg-rose-500' : s <= 40 ? 'bg-emerald-500' : 'bg-cyan-500'
})

function formatNum(n) { return n ? Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : '-' }
function formatPct(n) { return n ? Number(n).toFixed(2) : '0.00' }

async function loadData() {
  loading.value = true; error.value = null
  try {
    const [ov, ss] = await Promise.all([getOverview(), getSentimentSummary()])
    overview.value = ov.data; sentiment.value = ss.data
  } catch (e) { error.value = e.message || '网络错误，请稍后重试' }
  finally { loading.value = false }
}
onMounted(loadData)
</script>
