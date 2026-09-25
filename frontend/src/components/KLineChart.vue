<template>
  <div ref="chartRef" class="w-full bg-slate-900/60 rounded-xl border border-slate-800/60" style="height: 650px"></div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  klineData: { type: Array, default: () => [] },
  showMACD: { type: Boolean, default: true },
  showRSI: { type: Boolean, default: true },
  showKDJ: { type: Boolean, default: false },
  title: { type: String, default: '' },
})

const chartRef = ref(null)
let chart = null

const UP_COLOR = '#ef4444'
const DOWN_COLOR = '#22c55e'
const GRID_COLOR = '#1e293b'
const TEXT_COLOR = '#64748b'

function buildOption() {
  const dates = props.klineData.map(d => d.date)
  const ohlc = props.klineData.map(d => [d.open, d.close, d.low, d.high])
  const volumes = props.klineData.map(d => d.volume)

  // 4 个面板: K线(55%) | 成交量(15%) | MACD(15%) | RSI/KDJ(15%)
  const grids = [
    { left: '6%', right: '5%', top: 50, height: '52%' },        // K线
    { left: '6%', right: '5%', top: '70%', height: '10%' },      // 成交量
    { left: '6%', right: '5%', top: '82%', height: '8%' },       // MACD
    { left: '6%', right: '5%', top: '92%', height: '8%' },       // RSI/KDJ
  ]

  const xAxes = [
    { data: dates, gridIndex: 0, axisLine: { lineStyle: { color: GRID_COLOR } }, axisLabel: { color: TEXT_COLOR, fontSize: 10 }, axisTick: { show: false } },
    { data: dates, gridIndex: 1, axisLine: { show: false }, axisLabel: { show: false }, axisTick: { show: false } },
    { data: dates, gridIndex: 2, axisLine: { lineStyle: { color: GRID_COLOR } }, axisLabel: { color: TEXT_COLOR, fontSize: 10 }, axisTick: { show: false } },
    { data: dates, gridIndex: 3, axisLine: { lineStyle: { color: GRID_COLOR } }, axisLabel: { color: TEXT_COLOR, fontSize: 10 }, axisTick: { show: false } },
  ]

  const yAxes = [
    { gridIndex: 0, scale: true, splitLine: { lineStyle: { color: GRID_COLOR } }, axisLabel: { color: TEXT_COLOR, fontSize: 10 } },
    { gridIndex: 1, splitLine: { show: false }, axisLabel: { show: false }, axisTick: { show: false } },
    { gridIndex: 2, scale: true, splitLine: { lineStyle: { color: GRID_COLOR } }, axisLabel: { color: TEXT_COLOR, fontSize: 10 } },
    { gridIndex: 3, scale: true, splitLine: { lineStyle: { color: GRID_COLOR } }, axisLabel: { color: TEXT_COLOR, fontSize: 10 } },
  ]

  const series = []

  // === 主图: K线 ===
  series.push({
    name: 'K线', type: 'candlestick', data: ohlc, xAxisIndex: 0, yAxisIndex: 0,
    itemStyle: { color: UP_COLOR, color0: DOWN_COLOR, borderColor: UP_COLOR, borderColor0: DOWN_COLOR },
  })

  // 均线 (MA 5/20/60/120)
  const maColors = ['#fbbf24', '#60a5fa', '#a78bfa', '#34d399']
  ;[5, 20, 60, 120].forEach((p, idx) => {
    const data = dates.map((_, i) => {
      if (i < p - 1) return null
      const slice = ohlc.slice(i - p + 1, i + 1)
      const sum = slice.reduce((s, c) => s + c[1], 0)
      return [i, sum / p]
    })
    series.push({
      name: `MA${p}`, type: 'line', data, xAxisIndex: 0, yAxisIndex: 0,
      smooth: true, lineStyle: { width: 1, color: maColors[idx] }, symbol: 'none',
    })
  })

  // === 副图1: 成交量 ===
  series.push({
    name: 'VOL', type: 'bar', xAxisIndex: 1, yAxisIndex: 1,
    data: volumes.map((v, i) => [i, v, ohlc[i][1] > ohlc[i][0] ? 1 : -1]),
    itemStyle: { color: params => params.data[2] > 0 ? UP_COLOR : DOWN_COLOR },
  })

  // === 副图2: MACD ===
  if (props.showMACD) {
    // 手动算MACD用于副图
    const ema = (data, period) => {
      const k = 2 / (period + 1)
      const result = [data[0]]
      for (let i = 1; i < data.length; i++) result.push(data[i] * k + result[i - 1] * (1 - k))
      return result
    }
    const closes = props.klineData.map(d => d.close)
    const ema12 = ema(closes, 12)
    const ema26 = ema(closes, 26)
    const dif = ema12.map((v, i) => v - ema26[i])
    const dea = ema(dif, 9)
    const macd = dif.map((v, i) => (v - dea[i]) * 2)

    series.push({ name: 'DIF', type: 'line', data: dif.map((v, i) => [i, v]), xAxisIndex: 2, yAxisIndex: 2, lineStyle: { color: '#fbbf24', width: 1 }, symbol: 'none' })
    series.push({ name: 'DEA', type: 'line', data: dea.map((v, i) => [i, v]), xAxisIndex: 2, yAxisIndex: 2, lineStyle: { color: '#60a5fa', width: 1 }, symbol: 'none' })
    series.push({
      name: 'MACD', type: 'bar', xAxisIndex: 2, yAxisIndex: 2,
      data: macd.map((v, i) => [i, v]),
      itemStyle: { color: params => params.data[1] >= 0 ? UP_COLOR : DOWN_COLOR },
    })
  }

  // === 副图3: RSI 或 KDJ ===
  if (props.showRSI) {
    const closes = props.klineData.map(d => d.close)
    const calcRSI = (period) => {
      const gains = [], losses = [], rsi = []
      for (let i = 1; i < closes.length; i++) {
        const diff = closes[i] - closes[i - 1]
        gains.push(diff > 0 ? diff : 0)
        losses.push(diff < 0 ? -diff : 0)
      }
      let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period
      let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period
      for (let i = 0; i < period; i++) rsi.push(null)
      rsi.push(100 - 100 / (1 + avgGain / (avgLoss || 1)))
      for (let i = period; i < gains.length; i++) {
        avgGain = (avgGain * (period - 1) + gains[i]) / period
        avgLoss = (avgLoss * (period - 1) + losses[i]) / period
        rsi.push(100 - 100 / (1 + avgGain / (avgLoss || 1)))
      }
      return rsi
    }
    const rsi14 = calcRSI(14)
    series.push({
      name: 'RSI14', type: 'line', data: rsi14.map((v, i) => [i, v]), xAxisIndex: 3, yAxisIndex: 3,
      lineStyle: { color: '#c084fc', width: 1.5 }, symbol: 'none',
      markLine: { silent: true, data: [{ yAxis: 70, lineStyle: { color: GRID_COLOR, type: 'dashed' } }, { yAxis: 30, lineStyle: { color: GRID_COLOR, type: 'dashed' } }] }
    })
  }

  if (props.showKDJ) {
    const closes = props.klineData.map(d => d.close)
    const highs = props.klineData.map(d => d.high)
    const lows = props.klineData.map(d => d.low)
    const k = [], d = [], j = []
    for (let i = 0; i < closes.length; i++) {
      if (i < 8) { k.push(null); d.push(null); j.push(null); continue }
      const hh = Math.max(...highs.slice(i - 8, i + 1))
      const ll = Math.min(...lows.slice(i - 8, i + 1))
      const rsv = ((closes[i] - ll) / (hh - ll || 1)) * 100
      const kv = k.length && k[k.length - 1] ? (2 / 3) * k[k.length - 1] + (1 / 3) * rsv : rsv
      const dv = d.length && d[d.length - 1] ? (2 / 3) * d[d.length - 1] + (1 / 3) * kv : kv
      k.push(kv); d.push(dv); j.push(3 * kv - 2 * dv)
    }
    series.push({ name: 'K', type: 'line', data: k.map((v, i) => [i, v]), xAxisIndex: 3, yAxisIndex: 3, lineStyle: { color: '#fbbf24', width: 1 }, symbol: 'none' })
    series.push({ name: 'D', type: 'line', data: d.map((v, i) => [i, v]), xAxisIndex: 3, yAxisIndex: 3, lineStyle: { color: '#60a5fa', width: 1 }, symbol: 'none' })
    series.push({ name: 'J', type: 'line', data: j.map((v, i) => [i, v]), xAxisIndex: 3, yAxisIndex: 3, lineStyle: { color: '#c084fc', width: 1 }, symbol: 'none' })
  }

  return {
    backgroundColor: 'transparent',
    animation: false,
    color: [UP_COLOR, DOWN_COLOR],  // 全局色板: 红涨绿跌
    title: { text: props.title, left: 'center', top: 8, textStyle: { color: '#94a3b8', fontSize: 13, fontWeight: 'normal' } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    axisPointer: { link: [{ xAxisIndex: 'all' }] },
    grid: grids,
    xAxis: xAxes,
    yAxis: yAxes,
    series,
  }
}

onMounted(() => {
  chart = echarts.init(chartRef.value)
  chart.setOption(buildOption())
  window.addEventListener('resize', handleResize)
})

function handleResize() { chart?.resize() }

watch(() => [props.klineData, props.showMACD, props.showRSI, props.showKDJ], () => {
  if (chart) chart.setOption(buildOption(), true)
}, { deep: true })

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>
