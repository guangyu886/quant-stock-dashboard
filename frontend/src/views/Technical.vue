<template>
  <div class="space-y-4">
    <!-- 搜索栏 -->
    <div class="flex gap-2">
      <input v-model="symbol" @keyup.enter="search" placeholder="输入代码: sh600519 / AAPL / 00700"
        class="flex-1 bg-slate-900/80 border border-slate-700 rounded-lg px-4 py-2 text-sm text-white placeholder-slate-500 outline-none focus:border-blue-500" />
      <button @click="search"
        class="px-5 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors">
        查询
      </button>
    </div>

    <!-- K线图 -->
    <div v-if="loading" class="flex items-center justify-center py-32 text-slate-500">
      <span class="animate-pulse">加载中...</span>
    </div>
    <div v-else-if="klineData.length">
      <KLineChart :kline-data="klineData" :show-m-a-c-d="showMACD" :show-r-s-i="showRSI" :show-k-d-j="showKDJ"
        :title="`${symbol}`" />

      <!-- 底部控制 -->
      <div class="flex gap-2 mt-3 flex-wrap">
        <span class="text-xs text-slate-500 mr-1">副图指标:</span>
        <button @click="showMACD = !showMACD" :class="btnClass(showMACD)">MACD</button>
        <button @click="showRSI = !showRSI" :class="btnClass(showRSI)">RSI</button>
        <button @click="showKDJ = !showKDJ" :class="btnClass(showKDJ)">KDJ</button>
      </div>

      <!-- 信号列表 -->
      <div v-if="signals.length" class="mt-4 bg-slate-900/60 rounded-xl p-4 border border-slate-800/60">
        <div class="text-xs text-slate-500 mb-2">近期信号</div>
        <div class="space-y-1">
          <div v-for="s in signals.slice(-8)" :key="s.date + s.desc"
            class="flex items-center gap-2 text-sm py-0.5">
            <span class="text-xs text-slate-500 w-20">{{ s.date }}</span>
            <span :class="signalColor(s)">{{ s.desc }}</span>
            <span class="text-xs px-1.5 py-0.5 rounded" :class="strengthBadge(s.strength)">{{ s.strength }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-else-if="error" class="flex items-center justify-center py-32">
      <div class="text-center">
        <p class="text-rose-400 mb-2">⚠️ 查询失败</p>
        <p class="text-slate-500 text-sm">{{ error }}</p>
      </div>
    </div>
    <div v-else class="flex items-center justify-center py-32 text-slate-500">输入股票代码查看技术分析</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { getKline } from '../api'
import KLineChart from '../components/KLineChart.vue'

const symbol = ref('sh600519')
const klineData = ref([])
const signals = ref([])
const loading = ref(false)
const error = ref(null)
const showMACD = ref(true)
const showRSI = ref(true)
const showKDJ = ref(false)

function btnClass(active) {
  return `px-3 py-1 rounded text-xs transition-colors ${active ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`
}
function signalColor(s) {
  const bullish = ['golden_cross', 'macd_golden', 'oversold', 'squeeze_fire_long', 'wt_golden', 'elder_green', 'bullish_alignment', 'kdj_golden', 'vfi_turnover', 'supertrend_up', 'bb_breakdown']
  const bearish = ['dead_cross', 'macd_dead', 'overbought', 'squeeze_fire_short', 'wt_dead', 'elder_red', 'bearish_alignment', 'kdj_dead', 'supertrend_down', 'bb_breakout']
  if (bullish.some(t => s.type.includes(t) || s.desc.includes(t))) return 'text-emerald-400'
  if (bearish.some(t => s.type.includes(t) || s.desc.includes(t))) return 'text-rose-400'
  return 'text-slate-300'
}
function strengthBadge(s) {
  if (s === 'very_high') return 'bg-rose-500/20 text-rose-400'
  if (s === 'high') return 'bg-amber-500/20 text-amber-400'
  return 'bg-slate-800 text-slate-500'
}

async function search() {
  loading.value = true; error.value = null
  try {
    const res = await getKline(symbol.value, 'daily', 250, 'ma,macd,rsi,kdj')
    klineData.value = res.data.data
    signals.value = res.data.signals || []
  } catch (e) { error.value = e.response?.data?.detail || '查询失败，请检查代码是否正确' }
  finally { loading.value = false }
}
</script>
