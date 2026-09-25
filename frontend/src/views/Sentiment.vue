<template>
  <div v-if="loading" class="text-center py-20">
    <div class="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-3"></div>
    <p class="text-slate-500">正在加载情绪数据...</p>
  </div>
  <div v-else-if="error" class="text-center py-20">
    <p class="text-rose-400 mb-2">⚠️ 数据加载失败</p>
    <p class="text-slate-500 text-sm mb-4">{{ error }}</p>
    <button @click="loadData" class="px-4 py-2 bg-blue-600 rounded-lg text-white text-sm hover:bg-blue-700">重试</button>
  </div>
  <div v-else class="space-y-6">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="bg-slate-900/60 rounded-xl p-5 border border-slate-800/60 text-center">
        <div class="text-xs text-slate-500 mb-2">综合情绪指数</div>
        <div class="text-7xl font-bold tracking-tight" :class="color">{{ summary?.score || 50 }}</div>
        <div class="text-lg mt-2" :class="color">{{ summary?.level || '中性' }}</div>
        <div class="w-full bg-slate-800 rounded-full h-2 mt-5">
          <div class="h-2 rounded-full transition-all" :style="{ width: (summary?.score || 50) + '%' }"
            :class="summary?.score >= 60 ? 'bg-rose-500' : summary?.score <= 40 ? 'bg-emerald-500' : 'bg-cyan-500'"></div>
        </div>
        <div class="grid grid-cols-3 gap-2 mt-5 text-xs text-slate-500">
          <span>北向: {{ summary?.components?.north_flow }}</span>
          <span>涨跌: {{ summary?.components?.breadth }}</span>
          <span>VIX: {{ summary?.components?.vix }}</span>
        </div>
      </div>
      <div class="bg-slate-900/60 rounded-xl p-5 border border-slate-800/60">
        <h3 class="text-sm font-medium text-slate-400 mb-3">北向资金（近30日·亿元）</h3>
        <div ref="flowChart" class="w-full" style="height: 280px"></div>
      </div>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="bg-slate-900/60 rounded-xl p-4 border border-slate-800/60">
        <h3 class="text-xs text-slate-500 mb-2">涨跌比趋势</h3>
        <div ref="breadthChart" class="w-full" style="height: 220px"></div>
      </div>
      <div class="bg-slate-900/60 rounded-xl p-4 border border-slate-800/60">
        <h3 class="text-xs text-slate-500 mb-2">VIX 恐慌指数</h3>
        <div ref="vixChart" class="w-full" style="height: 220px"></div>
      </div>
      <div class="bg-slate-900/60 rounded-xl p-4 border border-slate-800/60">
        <h3 class="text-xs text-slate-500 mb-2">两市成交额（亿）</h3>
        <div ref="volumeChart" class="w-full" style="height: 220px"></div>
      </div>
    </div>
  </div><!-- end v-else -->
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import * as echarts from 'echarts'
import { getSentimentSummary, getFundFlow, getMarketBreadth, getVix } from '../api'

const summary = ref(null)
const flowChart = ref(null); const breadthChart = ref(null)
const vixChart = ref(null); const volumeChart = ref(null)
const loading = ref(true)
const error = ref(null)
const charts = []

const color = computed(() => {
  if (!summary.value) return 'text-slate-400'
  const s = summary.value.score
  if (s >= 75) return 'text-rose-400'; if (s >= 60) return 'text-amber-400'
  if (s >= 40) return 'text-cyan-400'
  return 'text-emerald-400'
})

const darkTheme = {
  backgroundColor: 'transparent',
  grid: { left: '8%', right: '5%', top: 15, bottom: 25 },
  xAxis: { type: 'category', axisLabel: { color: '#64748b', fontSize: 10 }, axisLine: { lineStyle: { color: '#334155' } } },
  yAxis: { splitLine: { lineStyle: { color: '#1e293b' } }, axisLabel: { color: '#64748b', fontSize: 10 } },
}

function line(name, data, k, color) {
  return { name, type: 'line', data: [...data].reverse().map(d => d[k]), smooth: true, lineStyle: { color, width: 2 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color }, { offset: 1, color: 'transparent' }]) }, symbol: 'none' }
}

onMounted(loadData)
window.addEventListener('resize', handleResize)

async function loadData() {
  loading.value = true; error.value = null
  try {
  const [ss, flow, breadth, vix] = await Promise.all([getSentimentSummary(), getFundFlow(30), getMarketBreadth('A', 30), getVix(30)])
  summary.value = ss.data

  function mk(el, series) {
    const c = echarts.init(el, 'dark'); charts.push(c)
    c.setOption({ ...darkTheme, tooltip: { trigger: 'axis' }, series: [series] })
  }
  if (flow.data.length) mk(flowChart.value, line('北向资金', flow.data, 'net_flow', '#f43f5e'))
  if (vix.data.length) mk(vixChart.value, line('VIX', vix.data, 'close', '#f59e0b'))
  if (breadth.data.length) {
    const c = echarts.init(breadthChart.value, 'dark'); charts.push(c)
    c.setOption({ ...darkTheme, tooltip: { trigger: 'axis' }, series: [{ name: '上涨比例', type: 'line', data: [...breadth.data].reverse().map(d => +(d.up_ratio * 100).toFixed(1)), smooth: true, lineStyle: { color: '#22c55e', width: 2 }, symbol: 'none' }], yAxis: { ...darkTheme.yAxis, axisLabel: { ...darkTheme.yAxis.axisLabel, formatter: '{value}%' } } })
  }
  if (breadth.data.length) {
    const c = echarts.init(volumeChart.value, 'dark'); charts.push(c)
    c.setOption({ ...darkTheme, tooltip: { trigger: 'axis' }, series: [{ name: '成交额', type: 'bar', data: [...breadth.data].reverse().map(d => d.total_volume), itemStyle: { color: '#6366f1' } }] })
  }
  } catch (e) { error.value = e.message || '网络错误，请稍后重试' }
  finally { loading.value = false }
}

function handleResize() {
  charts.forEach(c => { try { c.resize() } catch {} })
}

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  charts.forEach(c => c.dispose())
})
</script>
